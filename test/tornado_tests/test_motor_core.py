# Copyright 2016 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Validate list of PyMongo attributes wrapped by Motor."""

from test import env
from test.tornado_tests import MotorTest

from gridfs import GridFSBucket, GridIn
from tornado.testing import gen_test

from motor import MotorGridFSBucket, MotorGridIn


def attrs(klass):
    return set(a for a in dir(klass) if not a.startswith("_"))


motor_only = set(["delegate", "get_io_loop", "io_loop", "wrap"])

pymongo_only = set(["next"])

motor_client_only = motor_only.union(["open"])

pymongo_client_only = set([]).union(pymongo_only)

pymongo_database_only = set([]).union(pymongo_only)

pymongo_collection_only = set([]).union(pymongo_only)

motor_cursor_only = set(
    ["fetch_next", "to_list", "each", "started", "next_object", "closed"]
).union(motor_only)

pymongo_cursor_only = set(["retrieved"])


class MotorCoreTest(MotorTest):
    def test_client_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx) - pymongo_client_only, attrs(self.cx) - motor_client_only
        )

    @env.require_version_min(3, 6)
    @env.require_replica_set
    @gen_test
    async def test_client_session_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.start_session()), attrs((await self.cx.start_session())) - motor_only
        )

    def test_database_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test) - pymongo_database_only, attrs(self.cx.test) - motor_only
        )

    def test_collection_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test.test) - pymongo_collection_only,
            attrs(self.cx.test.test) - motor_only,
        )

    def test_cursor_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test.test.find()) - pymongo_cursor_only,
            attrs(self.cx.test.test.find()) - motor_cursor_only,
        )

    @env.require_replica_set
    @env.require_version_min(3, 6)
    def test_change_stream_attrs(self):
        # Ensure the database exists before creating a change stream.
        env.sync_cx.test.test.insert_one({})
        self.assertEqual(
            attrs(env.sync_cx.test.test.watch()), attrs(self.cx.test.test.watch()) - motor_only
        )

    @gen_test
    def test_command_cursor_attrs(self):
        motor_agg_cursor_only = set(["collection", "start", "args", "kwargs", "pipeline"]).union(
            motor_cursor_only
        )

        pymongo_cursor = env.sync_cx.test.test.aggregate([], cursor={})
        motor_cursor = self.cx.test.test.aggregate([])
        self.assertEqual(
            attrs(pymongo_cursor) - pymongo_cursor_only, attrs(motor_cursor) - motor_agg_cursor_only
        )


class MotorCoreTestGridFS(MotorTest):
    def setUp(self):
        super().setUp()
        self.sync_fs = GridFSBucket(env.sync_cx.test)
        self.sync_fs.upload_from_stream_with_id(1, "filename", source=b"")

    def tearDown(self):
        self.sync_fs.delete(file_id=1)
        super().tearDown()

    def test_gridfs_attrs(self):
        motor_gridfs_only = set(["collection"]).union(motor_only)

        self.assertEqual(
            attrs(GridFSBucket(env.sync_cx.test)),
            attrs(MotorGridFSBucket(self.cx.test)) - motor_gridfs_only,
        )

    def test_gridin_attrs(self):
        motor_gridin_only = set(["set"]).union(motor_only)
        gridin_only = set(["md5"])

        self.assertEqual(
            attrs(GridIn(env.sync_cx.test.fs)) - gridin_only,
            attrs(MotorGridIn(self.cx.test.fs)) - motor_gridin_only,
        )

    @gen_test
    async def test_gridout_attrs(self):
        motor_gridout_only = set(["open", "stream_to_handler"]).union(motor_only)

        gridin_only = set(
            [
                "md5",
                "readlines",
                "truncate",
                "flush",
                "fileno",
                "closed",
                "writelines",
                "isatty",
                "writable",
            ]
        )

        fs = MotorGridFSBucket(self.cx.test)
        motor_gridout = await fs.open_download_stream(1)
        self.assertEqual(
            attrs(self.sync_fs.open_download_stream(1)) - gridin_only,
            attrs(motor_gridout) - motor_gridout_only,
        )

    def test_gridout_cursor_attrs(self):
        self.assertEqual(
            attrs(self.sync_fs.find()) - pymongo_cursor_only,
            attrs(MotorGridFSBucket(self.cx.test).find()) - motor_cursor_only,
        )
