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
import gc
import sys
import unittest
import warnings
from unittest import SkipTest

from pymongo.errors import InvalidOperation, ExecutionTimeout
from pymongo.errors import OperationFailure
from mockupdb import OpQuery, OpKillCursors

from motor import motor_asyncio
from test.utils import one, safe_get
from test.asyncio_tests import (asyncio_test,
                                AsyncIOTestCase, AsyncIOMockServerTestCase,
                                server_is_mongos, at_least, get_command_line)


class TestAsyncIOCursor(AsyncIOMockServerTestCase):
    def test_cursor(self):
        cursor = self.collection.find()
        self.assertTrue(isinstance(cursor, motor_asyncio.AsyncIOMotorCursor))
        self.assertFalse(cursor.started, "Cursor shouldn't start immediately")

    @asyncio_test
    def test_count(self):
        yield from self.make_test_data()
        coll = self.collection
        self.assertEqual(200, (yield from coll.find().count()))
        self.assertEqual(
            100,
            (yield from coll.find({'_id': {'$gt': 99}}).count()))

        where = 'this._id % 2 == 0 && this._id >= 50'
        self.assertEqual(75, (yield from coll.find().where(where).count()))

    @asyncio_test
    def test_fetch_next(self):
        yield from self.make_test_data()
        coll = self.collection
        # 200 results, only including _id field, sorted by _id.
        cursor = coll.find({}, {'_id': 1}).sort('_id').batch_size(75)

        self.assertEqual(None, cursor.cursor_id)
        self.assertEqual(None, cursor.next_object())  # Haven't fetched yet.
        i = 0
        while (yield from cursor.fetch_next):
            self.assertEqual({'_id': i}, cursor.next_object())
            i += 1
            # With batch_size 75 and 200 results, cursor should be exhausted on
            # the server by third fetch.
            if i <= 150:
                self.assertNotEqual(0, cursor.cursor_id)
            else:
                self.assertEqual(0, cursor.cursor_id)

        self.assertEqual(False, (yield from cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(0, cursor.cursor_id)
        self.assertEqual(200, i)

    @unittest.skipUnless(sys.version_info >= (3, 4), "Python 3.4 required")
    @asyncio_test
    def test_fetch_next_delete(self):
        client, server = self.client_server(auto_ismaster={'ismaster': True})

        cursor = client.test.collection.find()
        self.fetch_next(cursor)
        request = yield from self.run_thread(server.receives, OpQuery)
        request.replies({'_id': 1}, cursor_id=123)

        # Decref the cursor and clear from the event loop.
        del cursor
        yield
        yield from self.run_thread(server.receives,
                                   OpKillCursors(cursor_ids=[123]))

    @asyncio_test
    def test_fetch_next_without_results(self):
        coll = self.collection
        # Nothing matches this query.
        cursor = coll.find({'foo': 'bar'})
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(False, (yield from cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        # Now cursor knows it's exhausted.
        self.assertEqual(0, cursor.cursor_id)

    @asyncio_test
    def test_fetch_next_is_idempotent(self):
        # Subsequent calls to fetch_next don't do anything
        yield from self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        self.assertEqual(None, cursor.cursor_id)
        yield from cursor.fetch_next
        self.assertTrue(cursor.cursor_id)
        self.assertEqual(101, cursor._buffer_size())
        yield from cursor.fetch_next  # Does nothing
        self.assertEqual(101, cursor._buffer_size())
        yield from cursor.close()

    @asyncio_test
    def test_fetch_next_exception(self):
        coll = self.collection
        cursor = coll.find()
        cursor.delegate._Cursor__id = 1234  # Not valid on server.

        with self.assertRaises(OperationFailure):
            yield from cursor.fetch_next

        # Avoid the cursor trying to close itself when it goes out of scope.
        cursor.delegate._Cursor__id = None

    @asyncio_test(timeout=30)
    def test_each(self):
        yield from self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1}).sort('_id')
        future = asyncio.Future(loop=self.loop)
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
        yield from future
        expected = [{'_id': i} for i in range(200)]
        self.assertEqual(expected, results)

    @asyncio_test
    def test_to_list_argument_checking(self):
        # We need more than 10 documents so the cursor stays alive.
        yield from self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        with self.assertRaises(ValueError):
            yield from cursor.to_list(-1)

        with self.assertRaises(TypeError):
            yield from cursor.to_list('foo')

    @asyncio_test
    def test_to_list_with_length(self):
        yield from self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort('_id')

        def expected(start, stop):
            return [{'_id': i} for i in range(start, stop)]

        self.assertEqual(expected(0, 10), (yield from cursor.to_list(10)))
        self.assertEqual(expected(10, 100), (yield from cursor.to_list(90)))

        # Test particularly rigorously around the 101-doc mark, since this is
        # where the first batch ends
        self.assertEqual(expected(100, 101), (yield from cursor.to_list(1)))
        self.assertEqual(expected(101, 102), (yield from cursor.to_list(1)))
        self.assertEqual(expected(102, 103), (yield from cursor.to_list(1)))
        self.assertEqual([], (yield from cursor.to_list(0)))
        self.assertEqual(expected(103, 105), (yield from cursor.to_list(2)))

        # Only 95 docs left, make sure length=100 doesn't error or hang
        self.assertEqual(expected(105, 200), (yield from cursor.to_list(100)))
        self.assertEqual(0, cursor.cursor_id)

        # Nothing left.
        self.assertEqual([], (yield from cursor.to_list(100)))

        yield from cursor.close()

    @asyncio_test
    def test_to_list_with_length_of_none(self):
        yield from self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        docs = yield from cursor.to_list(None)  # Unlimited.
        count = yield from collection.count()
        self.assertEqual(count, len(docs))

    @asyncio_test
    def test_to_list_tailable(self):
        coll = self.collection
        cursor = coll.find(tailable=True)

        # Can't call to_list on tailable cursor.
        with self.assertRaises(InvalidOperation):
            yield from cursor.to_list(10)

    @asyncio_test
    def test_cursor_explicit_close(self):
        client, server = self.client_server(auto_ismaster={'ismaster': True})
        collection = client.test.collection
        cursor = collection.find()

        future = self.fetch_next(cursor)
        self.assertTrue(cursor.alive)
        request = yield from self.run_thread(server.receives, OpQuery)
        request.replies({'_id': 1}, cursor_id=123)
        self.assertTrue((yield from future))
        self.assertEqual(123, cursor.cursor_id)

        future = self.ensure_future(cursor.close())

        # No reply to OP_KILLCURSORS.
        yield from self.run_thread(server.receives,
                                   OpKillCursors(cursor_ids=[123]))
        yield from future

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server.
        self.assertTrue(cursor.alive)
        self.assertEqual({'_id': 1}, cursor.next_object())
        self.assertFalse((yield from cursor.fetch_next))
        self.assertFalse(cursor.alive)

    @asyncio_test
    def test_each_cancel(self):
        yield from self.make_test_data()
        loop = self.loop
        collection = self.collection
        results = []
        future = asyncio.Future(loop=self.loop)

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
        yield from future
        self.assertEqual((yield from collection.count()), len(results))

    @asyncio_test
    def test_rewind(self):
        yield from self.collection.insert([{}, {}, {}])
        cursor = self.collection.find().limit(2)

        count = 0
        while (yield from cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield from cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield from cursor.fetch_next):
            cursor.next_object()
            break

        cursor.rewind()
        while (yield from cursor.fetch_next):
            cursor.next_object()
            count += 1

        self.assertEqual(2, count)
        self.assertEqual(cursor, cursor.rewind())

    @unittest.skipUnless(sys.version_info >= (3, 4), "Python 3.4 required")
    @asyncio_test
    def test_cursor_del(self):
        client, server = self.client_server(auto_ismaster=True)
        cursor = client.test.collection.find()

        future = self.fetch_next(cursor)
        request = yield from self.run_thread(server.receives, OpQuery)
        request.replies({'_id': 1}, cursor_id=123)
        yield from future  # Complete the first fetch.

        # Dereference the cursor.
        del cursor

        # Let the event loop iterate once more to clear its references to
        # callbacks, allowing the cursor to be freed.
        yield from asyncio.sleep(0, loop=self.loop)
        if 'PyPy' in sys.version:
            gc.collect()

        yield from self.run_thread(server.receives, OpKillCursors)

    @unittest.skipUnless(sys.version_info >= (3, 4), "Python 3.4 required")
    @asyncio_test
    def test_exhaust(self):
        if (yield from server_is_mongos(self.cx)):
            self.assertRaises(InvalidOperation,
                              self.db.test.find, exhaust=True)
            return

        self.assertRaises(TypeError, self.db.test.find, exhaust=5)

        cur = self.db.test.find(exhaust=True)
        self.assertRaises(InvalidOperation, cur.limit, 5)
        cur = self.db.test.find(limit=5)
        self.assertRaises(InvalidOperation, cur.add_option, 64)
        cur = self.db.test.find()
        cur.add_option(64)
        self.assertRaises(InvalidOperation, cur.limit, 5)

        yield from self.db.drop_collection("test")

        # Insert enough documents to require more than one batch.
        yield from self.db.test.insert([{} for _ in range(150)])

        client = self.asyncio_client(max_pool_size=1)
        # Ensure a pool.
        yield from client.db.collection.find_one()
        socks = client._get_primary_pool().sockets

        # Make sure the socket is returned after exhaustion.
        cur = client[self.db.name].test.find(exhaust=True)
        has_next = yield from cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))

        while (yield from cur.fetch_next):
            cur.next_object()

        self.assertEqual(1, len(socks))

        # Same as previous but with to_list instead of next_object.
        docs = yield from client[self.db.name].test.find(exhaust=True).to_list(
            None)
        self.assertEqual(1, len(socks))
        self.assertEqual(
            (yield from self.db.test.count()),
            len(docs))

        # If the Cursor instance is discarded before being
        # completely iterated we have to close and
        # discard the socket.
        sock = one(socks)
        cur = client[self.db.name].test.find(exhaust=True).batch_size(1)
        has_next = yield from cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))
        if 'PyPy' in sys.version:
            # Don't wait for GC or use gc.collect(), it's unreliable.
            cur.close()

        del cur

        yield from asyncio.sleep(0.1, loop=self.loop)

        # The exhaust cursor's socket was discarded, although another may
        # already have been opened to send OP_KILLCURSORS.
        self.assertNotIn(sock, socks)
        self.assertTrue(sock.closed)

    @asyncio_test
    def test_close_with_docs_in_batch(self):
        # MOTOR-67 Killed cursor with docs batched is "alive", don't kill again.
        yield from self.make_test_data()  # Ensure multiple batches.
        cursor = self.collection.find()
        yield from cursor.fetch_next
        yield from cursor.close()  # Killed but still "alive": has a batch.
        self.cx.close()

        with warnings.catch_warnings(record=True) as w:
            del cursor  # No-op, no error.

        self.assertEqual(0, len(w))


class TestAsyncIOCursorMaxTimeMS(AsyncIOTestCase):
    def setUp(self):
        super(TestAsyncIOCursorMaxTimeMS, self).setUp()
        self.loop.run_until_complete(self.maybe_skip())

    def tearDown(self):
        self.loop.run_until_complete(self.disable_timeout())
        super(TestAsyncIOCursorMaxTimeMS, self).tearDown()

    @asyncio.coroutine
    def maybe_skip(self):
        if (yield from server_is_mongos(self.cx)):
            raise SkipTest("mongos has no maxTimeAlwaysTimeOut fail point")

        if not (yield from at_least(self.cx, (2, 5, 3, -1))):
            raise SkipTest("maxTimeMS requires MongoDB >= 2.5.3")

        cmdline = yield from get_command_line(self.cx)
        if '1' != safe_get(cmdline, 'parsed.setParameter.enableTestCommands'):
            if 'enableTestCommands=1' not in cmdline['argv']:
                raise SkipTest("testing maxTimeMS requires failpoints")

    @asyncio.coroutine
    def enable_timeout(self):
        yield from self.cx.admin.command("configureFailPoint",
                                         "maxTimeAlwaysTimeOut",
                                         mode="alwaysOn")

    @asyncio.coroutine
    def disable_timeout(self):
        yield from self.cx.admin.command("configureFailPoint",
                                         "maxTimeAlwaysTimeOut",
                                         mode="off")

    @asyncio_test
    def test_max_time_ms_query(self):
        # Cursor parses server timeout error in response to initial query.
        yield from self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        with self.assertRaises(ExecutionTimeout):
            yield from cursor.fetch_next

        cursor = self.collection.find().max_time_ms(100000)
        with self.assertRaises(ExecutionTimeout):
            yield from cursor.to_list(10)

        with self.assertRaises(ExecutionTimeout):
            yield from self.collection.find_one(max_time_ms=100000)

    @asyncio_test(timeout=60)
    def test_max_time_ms_getmore(self):
        # Cursor handles server timeout during getmore, also.
        yield from self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            yield from cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield from self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                while (yield from cursor.fetch_next):
                    cursor.next_object()

            yield from cursor.close()

            # Send another initial query.
            yield from self.disable_timeout()
            cursor = self.collection.find().max_time_ms(100000)
            yield from cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield from self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                yield from cursor.to_list(None)

            # Avoid 'IOLoop is closing' warning.
            yield from cursor.close()
        finally:
            # Cleanup.
            yield from self.disable_timeout()
            yield from self.collection.remove()

    @asyncio_test
    def test_max_time_ms_each_query(self):
        # Cursor.each() handles server timeout during initial query.
        yield from self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        future = asyncio.Future(loop=self.loop)

        def callback(result, error):
            if error:
                future.set_exception(error)
            elif not result:
                # Done.
                future.set_result(None)

        with self.assertRaises(ExecutionTimeout):
            cursor.each(callback)
            yield from future

    @asyncio_test(timeout=30)
    def test_max_time_ms_each_getmore(self):
        # Cursor.each() handles server timeout during getmore.
        yield from self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            yield from cursor.fetch_next
            cursor.next_object()

            future = asyncio.Future(loop=self.loop)

            def callback(result, error):
                if error:
                    future.set_exception(error)
                elif not result:
                    # Done.
                    future.set_result(None)

            yield from self.enable_timeout()
            with self.assertRaises(ExecutionTimeout):
                cursor.each(callback)
                yield from future

            yield from cursor.close()
        finally:
            # Cleanup.
            yield from self.disable_timeout()
            yield from self.collection.remove()

    def test_iter(self):
        # Iteration should be prohibited.
        with self.assertRaises(TypeError):
            for _ in self.db.test.find():
                pass


if __name__ == '__main__':
    unittest.main()
