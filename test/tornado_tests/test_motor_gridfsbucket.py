# -*- coding: utf-8 -*-
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

"""Test MotorGridFSBucket."""

from io import BytesIO

from gridfs.errors import NoFile
from tornado import gen
from tornado.testing import gen_test

import motor
from test.tornado_tests import MotorTest


class MotorGridFSBucketTest(MotorTest):
    async def _reset(self):
        await self.db.drop_collection("fs.files")
        await self.db.drop_collection("fs.chunks")
        await self.db.drop_collection("alt.files")
        await self.db.drop_collection("alt.chunks")

    def setUp(self):
        super().setUp()
        self.io_loop.run_sync(self._reset)
        self.bucket = motor.MotorGridFSBucket(self.db)

    def tearDown(self):
        self.io_loop.run_sync(self._reset)
        super().tearDown()

    @gen_test
    async def test_basic(self):
        oid = await self.bucket.upload_from_stream("test_filename",
                                                   b"hello world")
        gout = await self.bucket.open_download_stream(oid)
        self.assertEqual(b"hello world", (await gout.read()))
        self.assertEqual(1, (await self.db.fs.files.count_documents({})))
        self.assertEqual(1, (await self.db.fs.chunks.count_documents({})))

        await self.bucket.delete(oid)
        with self.assertRaises(NoFile):
            await self.bucket.open_download_stream(oid)
        self.assertEqual(0, (await self.db.fs.files.count_documents({})))
        self.assertEqual(0, (await self.db.fs.chunks.count_documents({})))

        gin = self.bucket.open_upload_stream("test_filename")
        await gin.write(b"hello world")
        await gin.close()

        dst = BytesIO()
        await self.bucket.download_to_stream(gin._id, dst)
        self.assertEqual(b"hello world", dst.getvalue())

