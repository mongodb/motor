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

from __future__ import unicode_literals

"""Test MotorGridFSBucket."""

from io import BytesIO

from gridfs.errors import NoFile
from tornado import gen
from tornado.testing import gen_test

import motor
from test.tornado_tests import MotorTest


class MotorGridFSBucketTest(MotorTest):
    @gen.coroutine
    def _reset(self):
        yield self.db.drop_collection("fs.files")
        yield self.db.drop_collection("fs.chunks")
        yield self.db.drop_collection("alt.files")
        yield self.db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridFSBucketTest, self).setUp()
        self.io_loop.run_sync(self._reset)
        self.bucket = motor.MotorGridFSBucket(self.db)

    def tearDown(self):
        self.io_loop.run_sync(self._reset)
        super(MotorGridFSBucketTest, self).tearDown()

    @gen_test
    def test_basic(self):
        oid = yield self.bucket.upload_from_stream("test_filename",
                                                   b"hello world")
        gout = yield self.bucket.open_download_stream(oid)
        self.assertEqual(b"hello world", (yield gout.read()))
        self.assertEqual(1, (yield self.db.fs.files.count()))
        self.assertEqual(1, (yield self.db.fs.chunks.count()))

        yield self.bucket.delete(oid)
        with self.assertRaises(NoFile):
            yield self.bucket.open_download_stream(oid)
        self.assertEqual(0, (yield self.db.fs.files.count()))
        self.assertEqual(0, (yield self.db.fs.chunks.count()))

        gin = self.bucket.open_upload_stream("test_filename")
        yield gin.write(b"hello world")
        yield gin.close()

        dst = BytesIO()
        yield self.bucket.download_to_stream(gin._id, dst)
        self.assertEqual(b"hello world", dst.getvalue())

