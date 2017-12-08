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

from __future__ import unicode_literals

"""Validate list of PyMongo attributes wrapped by Motor."""

from tornado.testing import gen_test
from gridfs import GridFS, GridIn

from motor import MotorGridFS, MotorGridIn, MotorGridOut
from test import env
from test.tornado_tests import MotorTest


def attrs(klass):
    return set(a for a in dir(klass) if not a.startswith('_'))


motor_only = set([
    'delegate',
    'get_io_loop',
    'io_loop',
    'wrap'])

pymongo_only = set(['next'])

motor_client_only = motor_only.union(['open'])

pymongo_client_only = set([
    'is_locked',
    'set_cursor_manager']).union(pymongo_only)

pymongo_database_only = set([
    'system_js']).union(pymongo_only)

pymongo_collection_only = set([
    'aggregate_raw_batches',
    'find_raw_batches']).union(pymongo_only)

motor_cursor_only = set([
    'fetch_next',
    'to_list',
    'each',
    'started',
    'next_object',
    'closed']).union(motor_only)

pymongo_cursor_only = set(['retrieved']).union(pymongo_only)


class MotorCoreTest(MotorTest):
    def test_client_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx) - pymongo_client_only,
            attrs(self.cx) - motor_client_only)

    def test_database_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test) - pymongo_database_only,
            attrs(self.cx.test) - motor_only)

    def test_collection_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test.test) - pymongo_collection_only,
            attrs(self.cx.test.test) - motor_only)

    def test_cursor_attrs(self):
        self.assertEqual(
            attrs(env.sync_cx.test.test.find()) - pymongo_cursor_only,
            attrs(self.cx.test.test.find()) - motor_cursor_only)

    @env.require_replica_set
    @env.require_version_min(3, 6)
    def test_change_stream_attrs(self):
        # Ensure the database exists before creating a change stream.
        env.sync_cx.test.test.insert_one({})
        self.assertEqual(
            attrs(env.sync_cx.test.test.watch()),
            attrs(self.cx.test.test.watch()) - motor_only)

    @gen_test
    def test_command_cursor_attrs(self):
        motor_agg_cursor_only = set([
            'collection',
            'start',
            'args',
            'kwargs',
            'pipeline'
        ]).union(motor_cursor_only)

        pymongo_cursor = env.sync_cx.test.test.aggregate([], cursor={})
        motor_cursor = self.cx.test.test.aggregate([])
        self.assertEqual(
            attrs(pymongo_cursor) - pymongo_cursor_only,
            attrs(motor_cursor) - motor_agg_cursor_only)


class MotorCoreTestGridFS(MotorTest):
    def setUp(self):
        super(MotorCoreTestGridFS, self).setUp()
        self.sync_fs = GridFS(env.sync_cx.test)
        self.sync_fs.delete(file_id=1)
        self.sync_fs.put(b'', _id=1)

    def tearDown(self):
        self.sync_fs.delete(file_id=1)
        super(MotorCoreTestGridFS, self).tearDown()

    def test_gridfs_attrs(self):
        pymongo_gridfs_only = set([
            # Obsolete PyMongo methods.
            'open',
            'remove'])

        motor_gridfs_only = set(['collection']).union(motor_only)

        self.assertEqual(
            attrs(GridFS(env.sync_cx.test)) - pymongo_gridfs_only,
            attrs(MotorGridFS(self.cx.test)) - motor_gridfs_only)

    def test_gridin_attrs(self):
        motor_gridin_only = set(['set']).union(motor_only)

        self.assertEqual(
            attrs(GridIn(env.sync_cx.test.fs)),
            attrs(MotorGridIn(self.cx.test.fs)) - motor_gridin_only)

    @gen_test
    def test_gridout_attrs(self):
        motor_gridout_only = set([
            'open',
            'stream_to_handler'
        ]).union(motor_only)

        motor_gridout = yield MotorGridOut(self.cx.test.fs, file_id=1).open()
        self.assertEqual(
            attrs(self.sync_fs.get(1)),
            attrs(motor_gridout) - motor_gridout_only)

    def test_gridout_cursor_attrs(self):
        self.assertEqual(
            attrs(self.sync_fs.find()) - pymongo_cursor_only,
            attrs(MotorGridFS(self.cx.test).find()) - motor_cursor_only)
