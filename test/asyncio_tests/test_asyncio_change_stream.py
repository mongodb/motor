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

"""Test AsyncIOMotorChangeStream."""

import asyncio
import copy
import threading
import time

from pymongo.errors import InvalidOperation, OperationFailure

from motor.frameworks.asyncio import max_workers

from test import SkipTest, env
from test.asyncio_tests import asyncio_test, AsyncIOTestCase
from test.py35utils import wait_until
from test.utils import get_async_test_timeout


class TestAsyncIOChangeStream(AsyncIOTestCase):
    @classmethod
    @env.require_version_min(3, 6)
    def setUpClass(cls):
        super().setUpClass()
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
            timeout = get_async_test_timeout()
            while not change_stream.delegate:
                if time.time() - start > timeout:
                    print("MotorChangeStream never created ChangeStream")
                    return
                time.sleep(0.1)

            doclist = [{} for _ in range(n)] if isinstance(n, int) else n
            self.loop.call_soon_threadsafe(self.collection.insert_many, doclist)

        t = threading.Thread(target=target)
        t.daemon = True
        t.start()

    @asyncio_test
    async def test_async_for(self):
        change_stream = self.collection.watch()
        self.wait_and_insert(change_stream, 2)
        i = 0
        async for _ in change_stream:
            i += 1
            if i == 2:
                break

        self.assertEqual(i, 2)

    @asyncio_test
    async def test_async_for(self):
        change_stream = self.collection.watch()
        self.wait_and_insert(change_stream, 2)
        i = 0
        async for _ in change_stream:
            i += 1
            if i == 2:
                break

        self.assertEqual(i, 2)

    @asyncio_test
    async def test_async_try_next(self):
        change_stream = self.collection.watch()

        # No changes.
        doc = await change_stream.try_next()
        self.assertIsNone(doc)

        # Insert a change and ensure we see it via try_next.
        idoc = {'_id': 1, 'data': 'abc'}
        self.wait_and_insert(change_stream, [idoc])
        while change_stream.alive:
            change_doc = await change_stream.try_next()
            if change_doc is not None:
                break
        self.assertEqual(change_doc['fullDocument'], idoc)

    @env.require_version_min(4, 0, 7)
    @asyncio_test
    async def test_async_try_next_updates_resume_token(self):
        change_stream = self.collection.watch(
            [{"$match": {"fullDocument.a": 10}}])

        # Get empty change, check non-empty resume token.
        _ = await change_stream.try_next()
        self.assertIsNotNone(change_stream.resume_token)

        # Insert some record that don't match the change stream filter.
        self.wait_and_insert(change_stream, [{'a': 19}, {'a': 20}])

        # Ensure we see a new resume token even though we see no changes.
        initial_resume_token = copy.copy(change_stream.resume_token)
        async def token_change():
            _ = await change_stream.try_next()
            return change_stream.resume_token != initial_resume_token

        await wait_until(token_change, "see a new resume token",
                         timeout=get_async_test_timeout())

    @asyncio_test
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

    @env.require_version_min(4, 2)
    @asyncio_test
    async def test_watch_with_start_after(self):
        # Ensure collection exists before starting.
        await self.collection.insert_one({})

        # Create change stream before invalidate event.
        change_stream = self.collection.watch(
            [{'$match': {'operationType': 'invalidate'}}])
        _ = await change_stream.try_next()

        # Generate invalidate event and store corresponding resume token.
        await self.collection.drop()
        _ = await change_stream.next()
        self.assertFalse(change_stream.alive)
        resume_token = change_stream.resume_token

        # Recreate change stream and observe from invalidate event.
        doc = {'_id': 'startAfterTest'}
        await self.collection.insert_one(doc)
        change_stream = self.collection.watch(start_after=resume_token)
        change = await change_stream.next()
        self.assertEqual(doc, change['fullDocument'])

    @asyncio_test
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

    @asyncio_test
    async def test_missing_id(self):
        coll = self.collection
        change_stream = coll.watch([{'$project': {'_id': 0}}])
        future = change_stream.next()
        self.wait_and_insert(change_stream)
        with self.assertRaises((InvalidOperation, OperationFailure)):
            await future

        # The cursor should now be closed.
        with self.assertRaises(StopAsyncIteration):
            await change_stream.next()

    @asyncio_test
    async def test_unknown_full_document(self):
        coll = self.collection
        change_stream = coll.watch(full_document="unknownFullDocOption")
        future = change_stream.next()
        self.wait_and_insert(change_stream, 1)
        with self.assertRaises(OperationFailure):
            await future

    @asyncio_test
    async def test_async_with(self):
        async with self.collection.watch() as change_stream:
            self.wait_and_insert(change_stream, 1)
            async for _ in change_stream:
                self.assertTrue(change_stream.delegate._cursor.alive)
                break

        self.assertFalse(change_stream.delegate._cursor.alive)

    @asyncio_test
    async def test_async_with_creates_cursor(self):
        coll = self.collection
        await coll.insert_one({'_id': 1})
        async with coll.watch() as stream:
            self.assertEqual([{'_id': 1}],
                             await coll.find().to_list(None))
            await coll.insert_one({'_id': 2})
            doc = await stream.next()
            self.assertEqual({'_id': 2}, doc['fullDocument'])

    @asyncio_test
    async def test_with_statement(self):
        with self.assertRaises(RuntimeError):
            with self.collection.watch():
                pass

    @env.require_version_min(4, 0)
    @asyncio_test
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
    @asyncio_test
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

    @asyncio_test
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

    @asyncio_test(timeout=10)
    async def test_iterate_more_streams_than_workers(self):
        # Create more tasks running ChangeStream.next than there are worker
        # threads, and then ensure that other tasks can still run.
        streams = [self.collection.watch() for _ in range(max_workers)]
        tasks = [stream.next() for stream in streams]
        try:
            async def find_insert():
                # Wait for all change streams to be created
                while not all(stream.delegate for stream in streams):
                    await asyncio.sleep(.1)
                await self.collection.find_one()
                await self.collection.insert_one({})
            tasks.extend([find_insert() for _ in range(10)])
            await asyncio.gather(*tasks)
        finally:
            # Ensure that the .next() tasks always unblock.
            self.collection.delegate.insert_one({})
            for stream in streams:
                await stream.close()
