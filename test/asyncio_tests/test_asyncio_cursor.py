# Copyright 2014 MongoDB, Inc.
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

"""Test AsyncIOMotorCursor."""

import asyncio
import sys
import traceback
import unittest
import warnings
from functools import partial
from test.asyncio_tests import (
    AsyncIOMockServerTestCase,
    AsyncIOTestCase,
    asyncio_test,
    get_command_line,
    server_is_mongos,
)
from test.test_environment import env
from test.utils import (
    FailPoint,
    TestListener,
    get_async_test_timeout,
    get_primary_pool,
    one,
    safe_get,
    wait_until,
)
from unittest import SkipTest

import bson
from pymongo import CursorType
from pymongo.errors import ExecutionTimeout, InvalidOperation, OperationFailure

from motor import motor_asyncio


class TestAsyncIOCursor(AsyncIOMockServerTestCase):
    def test_cursor(self):
        cursor = self.collection.find()
        self.assertTrue(isinstance(cursor, motor_asyncio.AsyncIOMotorCursor))
        self.assertFalse(cursor.started, "Cursor shouldn't start immediately")

    @asyncio_test
    async def test_count(self):
        await self.make_test_data()
        coll = self.collection
        self.assertEqual(100, (await coll.count_documents({"_id": {"$gt": 99}})))

    @asyncio_test
    async def test_iterate(self):
        await self.make_test_data()
        coll = self.collection
        # 200 results, only including _id field, sorted by _id.
        cursor = coll.find({}, {"_id": 1}).sort("_id").batch_size(75)

        self.assertEqual(None, cursor.cursor_id)
        i = 0
        async for item in cursor:
            self.assertEqual({"_id": i}, item)
            i += 1
            # With batch_size 75 and 200 results, cursor should be exhausted on
            # the server by third fetch.
            if i <= 150:
                self.assertNotEqual(0, cursor.cursor_id)
            else:
                self.assertEqual(0, cursor.cursor_id)

        with self.assertRaises(StopAsyncIteration):
            await cursor.next()

        self.assertEqual(0, cursor.cursor_id)
        self.assertEqual(200, i)

    @unittest.skipIf("PyPy" in sys.version, "PyPy")
    @asyncio_test
    async def test_iterate_delete(self):
        client, server = self.client_server(auto_ismaster=True)

        cursor = client.test.coll.find()
        task = asyncio.create_task(cursor.next())
        request = await self.run_thread(server.receives, "find", "coll")
        request.replies({"cursor": {"id": 123, "ns": "db.coll", "firstBatch": [{"_id": 1}]}})

        await task

        # Decref the cursor and clear from the event loop.
        del cursor
        request = await self.run_thread(server.receives, "killCursors", "coll")

        request.ok()

    @asyncio_test
    async def test_iterate_exception(self):
        coll = self.collection
        await coll.insert_many([{} for _ in range(10)])
        cursor = coll.find(batch_size=2)
        item = await cursor.next()
        self.assertTrue(item)

        # Not valid on server, causes CursorNotFound.
        cursor.delegate._Cursor__id = bson.int64.Int64(1234)

        with self.assertRaises(OperationFailure):
            item = await cursor.next()
            self.assertTrue(item)
            item = await cursor.next()
            self.assertTrue(item)

    @asyncio_test(timeout=30)
    async def test_each(self):
        await self.make_test_data()
        cursor = self.collection.find({}, {"_id": 1}).sort("_id")
        future = self.loop.create_future()
        results = []

        def callback(result, error):
            if error:
                raise error

            if result is not None:
                results.append(result)
            else:
                # Done iterating.
                future.set_result(True)

        cursor.each(callback)
        await future
        expected = [{"_id": i} for i in range(200)]
        self.assertEqual(expected, results)

    @asyncio_test
    async def test_to_list_argument_checking(self):
        # We need more than 10 documents so the cursor stays alive.
        await self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        with self.assertRaises(ValueError):
            await cursor.to_list(-1)

        with self.assertRaises(TypeError):
            await cursor.to_list("foo")

    @asyncio_test
    async def test_to_list_with_length(self):
        await self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort("_id")

        def expected(start, stop):
            return [{"_id": i} for i in range(start, stop)]

        self.assertEqual(expected(0, 10), (await cursor.to_list(10)))
        self.assertEqual(expected(10, 100), (await cursor.to_list(90)))

        # Test particularly rigorously around the 101-doc mark, since this is
        # where the first batch ends
        self.assertEqual(expected(100, 101), (await cursor.to_list(1)))
        self.assertEqual(expected(101, 102), (await cursor.to_list(1)))
        self.assertEqual(expected(102, 103), (await cursor.to_list(1)))
        self.assertEqual([], (await cursor.to_list(0)))
        self.assertEqual(expected(103, 105), (await cursor.to_list(2)))

        # Only 95 docs left, make sure length=100 doesn't error or hang
        self.assertEqual(expected(105, 200), (await cursor.to_list(100)))
        self.assertEqual(0, cursor.cursor_id)

        # Nothing left.
        self.assertEqual([], (await cursor.to_list(100)))

        await cursor.close()

    @asyncio_test
    async def test_to_list_multiple_getMores(self):
        await self.make_test_data()
        coll = self.collection
        cursor = coll.find(batch_size=5).sort("_id")

        def expected(start, stop):
            return [{"_id": i} for i in range(start, stop)]

        # 2 batches (find+getMore):
        self.assertEqual(expected(0, 10), (await cursor.to_list(10)))
        # 5 batches, stop in the middle of a batch:
        self.assertEqual(expected(10, 33), (await cursor.to_list(23)))
        # 33 batches:
        self.assertEqual(expected(33, 200), (await cursor.to_list(167)))
        # Nothing left.
        self.assertEqual([], (await cursor.to_list(100)))

        await cursor.close()

    @asyncio_test
    async def test_to_list_exc_info(self):
        await self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        await cursor.to_list(length=10)
        await self.collection.drop()
        try:
            await cursor.to_list(length=None)
        except OperationFailure:
            _, _, tb = sys.exc_info()

            # The call tree should include PyMongo code we ran on a thread.
            formatted = "\n".join(traceback.format_tb(tb))
            self.assertTrue(
                "_unpack_response" in formatted or "_check_command_response" in formatted
            )

    async def _test_cancelled_error(self, coro):
        await self.make_test_data()
        # Cause an error on a getMore after the cursor.to_list task is
        # cancelled.
        fp = {
            "configureFailPoint": "failCommand",
            "data": {"failCommands": ["getMore"], "errorCode": 96},
            "mode": {"times": 1},
        }
        async with FailPoint(self.cx, fp):
            cleanup, task = coro(self.collection)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            await cleanup()
            # Yield for some time to allow pending Cursor callbacks to run.
            await asyncio.sleep(0.5)

    @env.require_version_min(4, 2)  # failCommand
    @asyncio_test
    async def test_cancelled_error_to_list(self):
        # Note: We intentionally don't use "async def" here to avoid wrapping
        # the returned to_list Future in a coroutine.
        def to_list(collection):
            cursor = collection.find(batch_size=2)
            return cursor.close, cursor.to_list(None)

        await self._test_cancelled_error(to_list)

    @env.require_version_min(4, 2)  # failCommand
    @asyncio_test
    async def test_cancelled_error_iterate(self):
        def fetch_next(collection):
            cursor = collection.find(batch_size=2)
            task = asyncio.create_task(cursor.next())
            return cursor.close, task

        await self._test_cancelled_error(fetch_next)

    @env.require_version_min(4, 2)  # failCommand
    @asyncio_test
    async def test_cancelled_error_iterate_aggregate(self):
        def fetch_next(collection):
            cursor = collection.aggregate([], batchSize=2)
            task = asyncio.create_task(cursor.next())
            return cursor.close, task

        await self._test_cancelled_error(fetch_next)

    @asyncio_test
    async def test_to_list_with_length_of_none(self):
        await self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        docs = await cursor.to_list(None)  # Unlimited.
        count = await collection.count_documents({})
        self.assertEqual(count, len(docs))

    @asyncio_test
    async def test_to_list_tailable(self):
        coll = self.collection
        cursor = coll.find(cursor_type=CursorType.TAILABLE)

        # Can't call to_list on tailable cursor.
        with self.assertRaises(InvalidOperation):
            await cursor.to_list(10)

    @asyncio_test
    async def test_cursor_explicit_close(self):
        client, server = self.client_server(auto_ismaster=True)
        collection = client.test.coll
        cursor = collection.find()

        task = asyncio.create_task(cursor.next())
        self.assertTrue(cursor.alive)
        request = await self.run_thread(server.receives, "find", "coll")
        request.replies({"cursor": {"id": 123, "ns": "db.coll", "firstBatch": [{"_id": 1}]}})

        self.assertTrue((await task))
        self.assertEqual(123, cursor.cursor_id)

        future = asyncio.ensure_future(cursor.close())

        # No reply to OP_KILLCURSORS.
        request = await self.run_thread(server.receives, "killCursors", "coll")

        request.ok()

        self.assertFalse(cursor.alive)

        await future
        item = await task
        self.assertEqual({"_id": 1}, item)

        with self.assertRaises(StopAsyncIteration):
            await cursor.next()

        self.assertFalse(cursor.alive)

    @asyncio_test
    async def test_each_cancel(self):
        await self.make_test_data()
        loop = self.loop
        collection = self.collection
        results = []
        future = self.loop.create_future()

        def cancel(result, error):
            if error:
                future.set_exception(error)

            else:
                results.append(result)
                loop.call_soon(canceled)
                return False  # Cancel iteration.

        def canceled():
            try:
                self.assertFalse(cursor.delegate._Cursor__killed)
                self.assertTrue(cursor.alive)

                # Resume iteration
                cursor.each(each)
            except Exception as e:
                future.set_exception(e)

        def each(result, error):
            if error:
                future.set_exception(error)
            elif result:
                pass
                results.append(result)
            else:
                # Complete
                future.set_result(None)

        cursor = collection.find()
        cursor.each(cancel)
        await future
        self.assertEqual((await collection.count_documents({})), len(results))

    @asyncio_test
    async def test_rewind(self):
        await self.collection.insert_many([{}, {}, {}])
        cursor = self.collection.find().limit(2)

        count = 0
        async for _ in cursor:
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        async for _ in cursor:
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        async for _ in cursor:
            break

        cursor.rewind()
        async for _ in cursor:
            count += 1

        self.assertEqual(2, count)
        self.assertEqual(cursor, cursor.rewind())

    @unittest.skipIf("PyPy" in sys.version, "PyPy")
    @asyncio_test
    async def test_cursor_del(self):
        client, server = self.client_server(auto_ismaster=True)
        cursor = client.test.coll.find()

        task = asyncio.create_task(cursor.next())
        request = await self.run_thread(server.receives, "find", "coll")
        request.replies({"cursor": {"id": 123, "ns": "db.coll", "firstBatch": [{"_id": 1}]}})
        await task  # Complete the first fetch.

        # Dereference the cursor.
        del cursor

        # Let the event loop iterate once more to clear its references to
        # callbacks, allowing the cursor to be freed.
        await asyncio.sleep(0)
        request = await self.run_thread(server.receives, "killCursors", "coll")

        request.ok()

    @asyncio_test
    async def test_exhaust(self):
        if await server_is_mongos(self.cx):
            self.assertRaises(InvalidOperation, self.db.test.find, cursor_type=CursorType.EXHAUST)
            return

        self.assertRaises(ValueError, self.db.test.find, cursor_type=5)

        cur = self.db.test.find(cursor_type=CursorType.EXHAUST)
        self.assertRaises(InvalidOperation, cur.limit, 5)
        cur = self.db.test.find(limit=5)
        self.assertRaises(InvalidOperation, cur.add_option, 64)
        cur = self.db.test.find()
        cur.add_option(64)
        self.assertRaises(InvalidOperation, cur.limit, 5)

        await self.db.drop_collection("test")

        # Insert enough documents to require more than one batch.
        await self.db.test.insert_many([{} for _ in range(150)])

        client = self.asyncio_client(maxPoolSize=1)
        # Ensure a pool.
        await client.db.collection.find_one()

        socks = get_primary_pool(client).sockets

        # Make sure the socket is returned after exhaustion.
        cur = client[self.db.name].test.find(cursor_type=CursorType.EXHAUST)
        item = await cur.next()
        self.assertTrue(item is not None)
        self.assertEqual(0, len(socks))

        async for _ in cur:
            pass

        self.assertEqual(1, len(socks))

        # Same as previous but with to_list instead of iteration.
        docs = await client[self.db.name].test.find(cursor_type=CursorType.EXHAUST).to_list(None)
        self.assertEqual(1, len(socks))
        self.assertEqual((await self.db.test.count_documents({})), len(docs))

        # If the Cursor instance is discarded before being
        # completely iterated we have to close and
        # discard the socket.
        sock = one(socks)
        cur = client[self.db.name].test.find(cursor_type=CursorType.EXHAUST).batch_size(1)
        item = await cur.next()
        self.assertTrue(item)
        # Run at least one getMore to initiate the OP_MSG exhaust protocol.
        if env.version.at_least(4, 2):
            item = await cur.next()
            self.assertTrue(item)
        self.assertEqual(0, len(socks))
        if "PyPy" in sys.version:
            # Don't wait for GC or use gc.collect(), it's unreliable.
            await cur.close()

        del cur

        async def sock_closed():
            return sock not in socks and sock.closed

        await wait_until(
            sock_closed, "close exhaust cursor socket", timeout=get_async_test_timeout()
        )

        # The exhaust cursor's socket was discarded, although another may
        # already have been opened to send OP_KILLCURSORS.
        self.assertNotIn(sock, socks)
        self.assertTrue(sock.closed)

    @asyncio_test
    async def test_close_with_docs_in_batch(self):
        # MOTOR-67 Killed cursor with docs batched is "alive", don't kill again.
        await self.make_test_data()  # Ensure multiple batches.
        cursor = self.collection.find()
        await cursor.next()
        await cursor.close()  # Killed but still "alive": has a batch.
        self.cx.close()

        with warnings.catch_warnings(record=True) as w:
            del cursor  # No-op, no error.

        self.assertEqual(0, len(w))

    @asyncio_test
    async def test_aggregate_batch_size(self):
        listener = TestListener()
        cx = self.asyncio_client(event_listeners=[listener])
        c = cx.motor_test.collection
        await c.delete_many({})
        await c.insert_many({"_id": i} for i in range(3))

        # Two ways of setting batchSize.
        cursor0 = c.aggregate([{"$sort": {"_id": 1}}]).batch_size(2)
        cursor1 = c.aggregate([{"$sort": {"_id": 1}}], batchSize=2)
        for cursor in cursor0, cursor1:
            lst = []
            async for item in cursor:
                lst.append(item)

            self.assertEqual(lst, [{"_id": 0}, {"_id": 1}, {"_id": 2}])
            aggregate = listener.first_command_started("aggregate")
            self.assertEqual(aggregate.command["cursor"]["batchSize"], 2)
            getMore = listener.first_command_started("getMore")
            self.assertEqual(getMore.command["batchSize"], 2)

    @asyncio_test
    async def test_raw_batches(self):
        c = self.collection
        await c.delete_many({})
        await c.insert_many({"_id": i} for i in range(4))

        find = partial(c.find_raw_batches, {})
        agg = partial(c.aggregate_raw_batches, [{"$sort": {"_id": 1}}])

        for method in find, agg:
            cursor = method().batch_size(2)
            batch = await cursor.next()
            self.assertEqual([{"_id": 0}, {"_id": 1}], bson.decode_all(batch))

            lst = await method().batch_size(2).to_list(length=1)
            self.assertEqual([{"_id": 0}, {"_id": 1}], bson.decode_all(lst[0]))


class TestAsyncIOCursorMaxTimeMS(AsyncIOTestCase):
    def setUp(self):
        super().setUp()
        self.loop.run_until_complete(self.maybe_skip())

    def tearDown(self):
        self.loop.run_until_complete(self.disable_timeout())
        super().tearDown()

    async def maybe_skip(self):
        if await server_is_mongos(self.cx):
            raise SkipTest("mongos has no maxTimeAlwaysTimeOut fail point")

        cmdline = await get_command_line(self.cx)
        if "1" != safe_get(cmdline, "parsed.setParameter.enableTestCommands"):
            if "enableTestCommands=1" not in cmdline["argv"]:
                raise SkipTest("testing maxTimeMS requires failpoints")

    async def enable_timeout(self):
        await self.cx.admin.command("configureFailPoint", "maxTimeAlwaysTimeOut", mode="alwaysOn")

    async def disable_timeout(self):
        await self.cx.admin.command("configureFailPoint", "maxTimeAlwaysTimeOut", mode="off")

    @asyncio_test
    async def test_max_time_ms_query(self):
        # Cursor parses server timeout error in response to initial query.
        await self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        with self.assertRaises(ExecutionTimeout):
            await cursor.next()

        cursor = self.collection.find().max_time_ms(100000)
        with self.assertRaises(ExecutionTimeout):
            await cursor.to_list(10)

        with self.assertRaises(ExecutionTimeout):
            await self.collection.find_one(max_time_ms=100000)

    @asyncio_test(timeout=60)
    async def test_max_time_ms_getmore(self):
        # Cursor handles server timeout during getmore, also.
        await self.collection.insert_many({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            await cursor.next()

            # Test getmore timeout.
            await self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                async for _ in cursor:
                    pass

            await cursor.close()

            # Send another initial query.
            await self.disable_timeout()
            cursor = self.collection.find().max_time_ms(100000)
            await cursor.next()

            # Test getmore timeout.
            await self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                await cursor.to_list(None)

            # Avoid 'IOLoop is closing' warning.
            await cursor.close()
        finally:
            # Cleanup.
            await self.disable_timeout()
            await self.collection.delete_many({})

    @asyncio_test
    async def test_max_time_ms_each_query(self):
        # Cursor.each() handles server timeout during initial query.
        await self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        future = self.loop.create_future()

        def callback(result, error):
            if error:
                future.set_exception(error)
            elif not result:
                # Done.
                future.set_result(None)

        with self.assertRaises(ExecutionTimeout):
            cursor.each(callback)
            await future

    @asyncio_test(timeout=30)
    async def test_max_time_ms_each_getmore(self):
        # Cursor.each() handles server timeout during getmore.
        await self.collection.insert_many({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            await cursor.next()

            future = self.loop.create_future()

            def callback(result, error):
                if error:
                    future.set_exception(error)
                elif not result:
                    # Done.
                    future.set_result(None)

            await self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                cursor.each(callback)
                await future

            await cursor.close()
        finally:
            # Cleanup.
            await self.disable_timeout()
            await self.collection.delete_many({})

    def test_iter(self):
        # Iteration should be prohibited.
        with self.assertRaises(TypeError):
            for _ in self.db.test.find():
                pass


if __name__ == "__main__":
    unittest.main()
