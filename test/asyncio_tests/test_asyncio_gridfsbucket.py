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

"""Test AsyncIOMotorGridFSBucket."""

import asyncio
from io import BytesIO

from gridfs.errors import NoFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from test.asyncio_tests import AsyncIOTestCase, asyncio_test


class TestAsyncIOGridFSBucket(AsyncIOTestCase):
    @asyncio.coroutine
    def _reset(self):
        yield from self.db.drop_collection("fs.files")
        yield from self.db.drop_collection("fs.chunks")
        yield from self.db.drop_collection("alt.files")
        yield from self.db.drop_collection("alt.chunks")

    def setUp(self):
        super(TestAsyncIOGridFSBucket, self).setUp()
        self.loop.run_until_complete(self._reset())
        self.bucket = AsyncIOMotorGridFSBucket(self.db)

    def tearDown(self):
        self.loop.run_until_complete(self._reset())
        super(TestAsyncIOGridFSBucket, self).tearDown()

    @asyncio_test
    def test_basic(self):
        oid = yield from self.bucket.upload_from_stream("test_filename",
                                                        b"hello world")
        gout = yield from self.bucket.open_download_stream(oid)
        self.assertEqual(b"hello world", (yield from gout.read()))
        self.assertEqual(1, (yield from self.db.fs.files.count()))
        self.assertEqual(1, (yield from self.db.fs.chunks.count()))

        dst = BytesIO()
        yield from self.bucket.download_to_stream(gout._id, dst)
        self.assertEqual(b"hello world", dst.getvalue())

        yield from self.bucket.delete(oid)
        with self.assertRaises(NoFile):
            yield from self.bucket.open_download_stream(oid)
        self.assertEqual(0, (yield from self.db.fs.files.count()))
        self.assertEqual(0, (yield from self.db.fs.chunks.count()))
