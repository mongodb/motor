# Copyright 2017-present MongoDB, Inc.
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

from __future__ import absolute_import, unicode_literals

"""Test MotorChangeStream."""

import os
import threading
import time

from pymongo.errors import InvalidOperation, OperationFailure
from tornado.testing import gen_test

from test import SkipTest, env
from test.tornado_tests import MotorTest


class MotorChangeStreamTest(MotorTest):
    @classmethod
    @env.require_version_min(3, 6)
    def setUpClass(cls):
        super(MotorChangeStreamTest, cls).setUpClass()
        if env.is_standalone:
            raise SkipTest("Standalone")

        # Ensure the collection exists.
        env.sync_cx.motor_test.test_collection.delete_many({})
        env.sync_cx.motor_test.test_collection.insert_one({'_id': 1})

    def wait_and_insert(self, change_stream, n=1):
        # The start time of the change stream is nondeterministic. Wait
        # to ensure this insert comes after the change stream starts.

        def target():
            start = time.time()
            timeout = float(os.environ.get('ASYNC_TEST_TIMEOUT', 5))
            while not change_stream.delegate:
                if time.time() - start > timeout:
                    print("MotorChangeStream never created ChangeStream")
                    return
                time.sleep(0.1)

            self.io_loop.add_callback(self.collection.insert_many,
                                      [{} for _ in range(n)])

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()

    @gen_test
    async def test_async_for(self):
        change_stream = self.collection.watch()
        self.wait_and_insert(change_stream, 2)
        i = 0
        async for _ in change_stream:
            i += 1
            if i == 2:
                break

        self.assertEqual(i, 2)

    @gen_test
    async def test_watch(self):
        coll = self.collection

        with self.assertRaises(TypeError):
            # pipeline must be a list.
            async for _ in coll.watch(pipeline={}):
                pass

        change_stream = coll.watch()
        self.wait_and_insert(change_stream, 1)
        change = await change_stream.next()

        # New change stream with resume token.
        await coll.insert_one({'_id': 23})
        change = await coll.watch(resume_after=change['_id']).next()
        self.assertEqual(change['fullDocument'], {'_id': 23})

    @gen_test
    async def test_close(self):
        coll = self.collection
        change_stream = coll.watch()
        future = change_stream.next()
        self.wait_and_insert(change_stream, 1)
        await future

        await change_stream.close()
        with self.assertRaises(StopAsyncIteration):
            await change_stream.next()

        async for _ in change_stream:
            pass

    @gen_test
    async def test_missing_id(self):
        coll = self.collection
        change_stream = coll.watch([{'$project': {'_id': 0}}])
        future = change_stream.next()
        self.wait_and_insert(change_stream)
        with self.assertRaises(InvalidOperation):
            await future

        # The cursor should now be closed.
        with self.assertRaises(StopAsyncIteration):
            await change_stream.next()

    @gen_test
    async def test_unknown_full_document(self):
        coll = self.collection
        change_stream = coll.watch(full_document="unknownFullDocOption")
        future = change_stream.next()
        self.wait_and_insert(change_stream, 1)
        with self.assertRaises(OperationFailure):
            await future

    @gen_test
    async def test_async_with(self):
        async with self.collection.watch() as change_stream:
            self.wait_and_insert(change_stream, 1)
            async for _ in change_stream:
                self.assertTrue(change_stream.delegate._cursor.alive)
                break

        self.assertFalse(change_stream.delegate._cursor.alive)

    @gen_test
    async def test_with_statement(self):
        with self.assertRaises(RuntimeError):
            with self.collection.watch():
                pass
