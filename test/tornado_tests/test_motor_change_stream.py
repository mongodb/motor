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

"""Test MotorChangeStream."""

import copy
import threading
import time
import unittest
from test import SkipTest, env
from test.tornado_tests import MotorTest
from test.utils import get_async_test_timeout, wait_until

from pymongo.errors import InvalidOperation, OperationFailure
from tornado.testing import gen_test


class MotorChangeStreamTest(MotorTest):
    @classmethod
    @env.require_version_min(3, 6)
    def setUpClass(cls):
        super().setUpClass()
        if env.is_standalone:
            raise SkipTest("Standalone")

        # Ensure the collection exists.
        env.sync_cx.motor_test.test_collection.delete_many({})
        env.sync_cx.motor_test.test_collection.insert_one({"_id": 1})

    def wait_and_insert(self, change_stream, n=1):
        # The start time of the change stream is nondeterministic. Wait
        # to ensure this insert comes after the change stream starts.

        def target():
            start = time.time()
            timeout = get_async_test_timeout()
            while not change_stream.delegate:
                if time.time() - start > timeout:
                    print("MotorChangeStream never created ChangeStream")
                    return
                time.sleep(0.1)

            doclist = [{} for _ in range(n)] if isinstance(n, int) else n
            self.io_loop.add_callback(self.collection.insert_many, doclist)

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
    async def test_async_try_next(self):
        change_stream = self.collection.watch()

        # No changes.
        doc = await change_stream.try_next()
        self.assertIsNone(doc)

        # Insert a change and ensure we see it via try_next.
        idoc = {"_id": 1, "data": "abc"}
        self.wait_and_insert(change_stream, [idoc])
        while change_stream.alive:
            change_doc = await change_stream.try_next()
            if change_doc is not None:
                break
        self.assertEqual(change_doc["fullDocument"], idoc)

    @env.require_version_min(4, 0, 7)
    @gen_test
    async def test_async_try_next_updates_resume_token(self):
        change_stream = self.collection.watch([{"$match": {"fullDocument.a": 10}}])

        # Get empty change, check non-empty resume token.
        _ = await change_stream.try_next()
        self.assertIsNotNone(change_stream.resume_token)

        # Insert some record that don't match the change stream filter.
        self.wait_and_insert(change_stream, [{"a": 19}, {"a": 20}])

        # Ensure we see a new resume token even though we see no changes.
        initial_resume_token = copy.copy(change_stream.resume_token)

        async def token_change():
            _ = await change_stream.try_next()
            return change_stream.resume_token != initial_resume_token

        await wait_until(token_change, "see a new resume token", timeout=get_async_test_timeout())

    @gen_test
    async def test_watch(self):
        coll = self.collection

        with self.assertRaises(TypeError):
            # pipeline must be a list.
            async for _ in coll.watch(pipeline={}):
                pass

        change_stream = coll.watch()
        future = change_stream.next()
        self.wait_and_insert(change_stream, 1)
        change = await future

        # New change stream with resume token.
        await coll.insert_one({"_id": 23})
        change = await coll.watch(resume_after=change["_id"]).next()
        self.assertEqual(change["fullDocument"], {"_id": 23})

    @env.require_version_min(4, 2)
    @gen_test
    async def test_watch_with_start_after(self):
        # Ensure collection exists before starting.
        await self.collection.insert_one({})

        # Create change stream before invalidate event.
        change_stream = self.collection.watch([{"$match": {"operationType": "invalidate"}}])
        _ = await change_stream.try_next()

        # Generate invalidate event and store corresponding resume token.
        await self.collection.drop()
        _ = await change_stream.next()
        # v5.1 requires an extra getMore after an invalidate event to exhaust
        # the cursor.
        self.assertIsNone(await change_stream.try_next())
        self.assertFalse(change_stream.alive)
        resume_token = change_stream.resume_token

        # Recreate change stream and observe from invalidate event.
        doc = {"_id": "startAfterTest"}
        await self.collection.insert_one(doc)
        change_stream = self.collection.watch(start_after=resume_token)
        change = await change_stream.next()
        self.assertEqual(doc, change["fullDocument"])

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
    @unittest.skip("Failing due to: https://jira.mongodb.org/browse/PYTHON-3389.")
    async def test_missing_id(self):
        coll = self.collection
        change_stream = coll.watch([{"$project": {"_id": 0}}])
        future = change_stream.next()
        self.wait_and_insert(change_stream)
        with self.assertRaises((InvalidOperation, OperationFailure)):
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

    @env.require_version_min(4, 0)
    @gen_test
    async def test_client(self):
        change_stream = self.cx.watch()
        self.wait_and_insert(change_stream, 2)
        i = 0
        async for _ in change_stream:
            i += 1
            if i == 2:
                break

        await self.cx.other_db.other_collection.insert_one({})
        async for _ in change_stream:
            i += 1
            if i == 3:
                break

    @env.require_version_min(4, 0)
    @gen_test
    async def test_database(self):
        change_stream = self.db.watch()
        self.wait_and_insert(change_stream, 2)
        i = 0
        async for _ in change_stream:
            i += 1
            if i == 2:
                break

        await self.db.other_collection.insert_one({})
        async for _ in change_stream:
            i += 1
            if i == 3:
                break

    @gen_test
    async def test_watch_with_session(self):
        async with await self.cx.start_session() as session:
            # Pass MotorSession.
            async with self.collection.watch(session=session) as cs:
                self.wait_and_insert(cs, 1)
                _ = await cs.next()
            # Pass PyMongo session directly.
            async with self.collection.watch(session=session.delegate) as cs:
                self.wait_and_insert(cs, 1)
                _ = await cs.next()
