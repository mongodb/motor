# Copyright 2012-2014 MongoDB, Inc.
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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import datetime
import sys
import unittest
from functools import partial

import greenlet
import pymongo
from tornado import gen
from pymongo.errors import InvalidOperation, ExecutionTimeout
from pymongo.errors import OperationFailure
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
from test import MotorTest, assert_raises, SkipTest
from test.utils import server_is_mongos, version, get_command_line


class MotorCursorTest(MotorTest):
    def test_cursor(self):
        cursor = self.collection.find()
        self.assertTrue(isinstance(cursor, motor.MotorCursor))
        self.assertFalse(cursor.started, "Cursor shouldn't start immediately")

    @gen_test
    def test_count_callback(self):
        yield self.check_optional_callback(self.collection.find().count)

    @gen_test
    def test_count(self):
        yield self.make_test_data()
        coll = self.collection
        self.assertEqual(200, (yield coll.find().count()))
        self.assertEqual(100, (yield coll.find({'_id': {'$gt': 99}}).count()))
        where = 'this._id % 2 == 0 && this._id >= 50'
        self.assertEqual(75, (yield coll.find({'$where': where}).count()))
        self.assertEqual(75, (yield coll.find().where(where).count()))
        self.assertEqual(
            25,
            (yield coll.find({'_id': {'$lt': 100}}).where(where).count()))

        self.assertEqual(
            25,
            (yield coll.find({'_id': {'$lt': 100}, '$where': where}).count()))

    @gen_test
    def test_fetch_next(self):
        yield self.make_test_data()
        coll = self.collection
        # 200 results, only including _id field, sorted by _id
        cursor = coll.find({}, {'_id': 1}).sort(
            [('_id', pymongo.ASCENDING)]).batch_size(75)

        self.assertEqual(None, cursor.cursor_id)
        self.assertEqual(None, cursor.next_object())  # Haven't fetched yet
        i = 0
        while (yield cursor.fetch_next):
            self.assertEqual({'_id': i}, cursor.next_object())
            i += 1
            # With batch_size 75 and 200 results, cursor should be exhausted on
            # the server by third fetch
            if i <= 150:
                self.assertNotEqual(0, cursor.cursor_id)
            else:
                self.assertEqual(0, cursor.cursor_id)

        self.assertEqual(False, (yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(0, cursor.cursor_id)
        self.assertEqual(200, i)

    @gen_test(timeout=30)
    def test_fetch_next_delete(self):
        coll = self.collection
        yield coll.insert({})

        # Decref'ing the cursor eventually closes it on the server; yielding
        # clears the engine Runner's reference to the cursor.
        cursor = coll.find().batch_size(1)
        yield cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved
        del cursor
        yield gen.Task(self.io_loop.add_callback)
        yield self.wait_for_cursor(coll, cursor_id, retrieved)

    @gen_test
    def test_fetch_next_without_results(self):
        coll = self.collection
        # Nothing matches this query
        cursor = coll.find({'foo': 'bar'})
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(False, (yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        # Now cursor knows it's exhausted
        self.assertEqual(0, cursor.cursor_id)

    @gen_test
    def test_fetch_next_is_idempotent(self):
        # Subsequent calls to fetch_next don't do anything
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        self.assertEqual(None, cursor.cursor_id)
        yield cursor.fetch_next
        self.assertTrue(cursor.cursor_id)
        self.assertEqual(101, cursor._buffer_size())
        yield cursor.fetch_next  # Does nothing
        self.assertEqual(101, cursor._buffer_size())

    @gen_test
    def test_fetch_next_exception(self):
        coll = self.collection
        cursor = coll.find()
        cursor.delegate._Cursor__id = 1234  # Not valid on server

        with assert_raises(OperationFailure):
            yield cursor.fetch_next

        # Avoid the cursor trying to close itself when it goes out of scope
        cursor.delegate._Cursor__id = None

    @gen_test
    def test_each_callback(self):
        cursor = self.collection.find()
        self.assertRaises(TypeError, cursor.each, callback='foo')
        self.assertRaises(TypeError, cursor.each, callback=None)
        self.assertRaises(TypeError, cursor.each)  # No callback.

        # Should not raise
        (result, error), _ = yield gen.Task(cursor.each)
        if error:
            raise error

    @gen_test
    def test_each(self):
        yield self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1})
        cursor.sort([('_id', pymongo.ASCENDING)])
        future = Future()
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
        yield future
        expected = [{'_id': i} for i in range(200)]
        self.assertEqual(expected, results)

    @gen_test
    def test_to_list_argument_checking(self):
        # We need more than 10 documents so the cursor stays alive.
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find()
        yield self.check_optional_callback(cursor.to_list, 10)
        cursor = coll.find()
        with assert_raises(ValueError):
            yield cursor.to_list(-1)

        with assert_raises(TypeError):
            yield cursor.to_list('foo')

    @gen_test
    def test_to_list_callback(self):
        yield self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1})
        cursor.sort([('_id', pymongo.ASCENDING)])
        expected = [{'_id': i} for i in range(200)]
        (result, error), _ = yield gen.Task(cursor.to_list, length=1000)
        self.assertEqual(expected, result)

        cursor = self.collection.find().where('return foo')
        (result, error), _ = yield gen.Task(cursor.to_list, length=1000)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, OperationFailure))

    @gen_test
    def test_to_list_with_length(self):
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort('_id')
        self.assertEqual([], (yield cursor.to_list(0)))

        def expected(start, stop):
            return [{'_id': i} for i in range(start, stop)]

        self.assertEqual(expected(0, 10), (yield cursor.to_list(10)))
        self.assertEqual(expected(10, 100), (yield cursor.to_list(90)))

        # Test particularly rigorously around the 101-doc mark, since this is
        # where the first batch ends
        self.assertEqual(expected(100, 101), (yield cursor.to_list(1)))
        self.assertEqual(expected(101, 102), (yield cursor.to_list(1)))
        self.assertEqual(expected(102, 103), (yield cursor.to_list(1)))
        self.assertEqual([], (yield cursor.to_list(0)))
        self.assertEqual(expected(103, 105), (yield cursor.to_list(2)))

        # Only 95 docs left, make sure length=100 doesn't error or hang
        self.assertEqual(expected(105, 200), (yield cursor.to_list(100)))
        self.assertEqual(0, cursor.cursor_id)

    @gen_test
    def test_to_list_with_length_of_none(self):
        yield self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        docs = yield cursor.to_list(None)  # Unlimited.
        count = yield collection.count()
        self.assertEqual(count, len(docs))

    @gen_test
    def test_to_list_tailable(self):
        coll = self.collection
        cursor = coll.find(tailable=True)

        # Can't call to_list on tailable cursor.
        with assert_raises(InvalidOperation):
            yield cursor.to_list(10)

    @gen_test
    def test_limit_zero(self):
        # Limit of 0 is a weird case that PyMongo handles specially, make sure
        # Motor does too. cursor.limit(0) means "remove limit", but cursor[:0]
        # or cursor[5:5] sets the cursor to "empty".
        coll = self.collection
        yield coll.insert({'_id': 1})

        self.assertEqual(False, (yield coll.find()[:0].fetch_next))
        self.assertEqual(False, (yield coll.find()[5:5].fetch_next))

        # each() with limit 0 runs its callback once with args (None, None).
        (result, error), _ = yield gen.Task(coll.find()[:0].each)
        self.assertEqual((None, None), (result, error))
        (result, error), _ = yield gen.Task(coll.find()[:0].each)
        self.assertEqual((None, None), (result, error))

        self.assertEqual([], (yield coll.find()[:0].to_list(length=1000)))
        self.assertEqual([], (yield coll.find()[5:5].to_list(length=1000)))

    @gen_test(timeout=10)
    def test_cursor_explicit_close(self):
        yield self.make_test_data()
        collection = self.collection
        yield self.check_optional_callback(collection.find().close)
        cursor = collection.find()
        yield cursor.fetch_next
        self.assertTrue(cursor.alive)

        # OP_KILL_CURSORS is sent asynchronously to the server, no ack.
        yield cursor.close()

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server
        self.assertTrue(cursor.alive)
        retrieved = cursor.delegate._Cursor__retrieved

        # We'll check the cursor is closed by trying getMores on it until the
        # server returns CursorNotFound. However, if we're in the midst of a
        # getMore when the asynchronous OP_KILL_CURSORS arrives, the server
        # won't kill the cursor. It logs "Assertion: 16089:Cannot kill active
        # cursor." So wait for OP_KILL_CURSORS to reach the server first.
        yield self.pause(5)
        yield self.wait_for_cursor(collection, cursor.cursor_id, retrieved)

    @gen_test
    def test_each_cancel(self):
        yield self.make_test_data()
        loop = self.io_loop
        collection = self.collection
        results = []
        future = Future()

        def cancel(result, error):
            if error:
                future.set_exception(error)

            else:
                results.append(result)
                loop.add_callback(canceled)
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
        yield future
        self.assertEqual((yield collection.count()), len(results))

    @gen_test
    def test_each_close(self):
        yield self.make_test_data()  # 200 documents.
        loop = self.io_loop
        collection = self.collection
        results = []
        future = Future()

        def callback(result, error):
            if error:
                future.set_exception(error)

            else:
                results.append(result)
                if len(results) == 50:
                    # Prevent further calls.
                    cursor.close()

                    # Soon, finish this test. Leave a little time for further
                    # calls to ensure we've really canceled them by calling
                    # cursor.close().
                    loop.add_timeout(
                        datetime.timedelta(milliseconds=10),
                        partial(future.set_result, None))

        cursor = collection.find()
        cursor.each(callback)
        yield future
        self.assertEqual(50, len(results))

    def test_cursor_slice_argument_checking(self):
        collection = self.collection

        for arg in '', None, {}, []:
            self.assertRaises(TypeError, lambda: collection.find()[arg])

        self.assertRaises(IndexError, lambda: collection.find()[-1])

    @gen_test
    def test_cursor_slice(self):
        # This is an asynchronous copy of PyMongo's test_getitem_slice_index in
        # test_cursor.py
        yield self.make_test_data()
        coll = self.collection

        self.assertRaises(IndexError, lambda: coll.find()[-1])
        self.assertRaises(IndexError, lambda: coll.find()[1:2:2])
        self.assertRaises(IndexError, lambda: coll.find()[2:1])

        result = yield coll.find()[0:].to_list(length=1000)
        self.assertEqual(200, len(result))

        result = yield coll.find()[20:].to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find()[99:].to_list(length=1000)
        self.assertEqual(101, len(result))

        result = yield coll.find()[1000:].to_list(length=1000)
        self.assertEqual(0, len(result))

        result = yield coll.find()[20:25].to_list(length=1000)
        self.assertEqual(5, len(result))

        # Any slice overrides all previous slices
        result = yield coll.find()[20:25][20:].to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find()[20:25].limit(0).skip(20).to_list(length=1000)
        self.assertEqual(180, len(result))

        result = yield coll.find().limit(0).skip(20)[20:25].to_list(length=1000)
        self.assertEqual(5, len(result))

        result = yield coll.find()[:1].to_list(length=1000)
        self.assertEqual(1, len(result))

        result = yield coll.find()[:5].to_list(length=1000)
        self.assertEqual(5, len(result))

    @gen_test(timeout=30)
    def test_cursor_index(self):
        yield self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort([('_id', 1)])[0]
        yield cursor.fetch_next
        self.assertEqual({'_id': 0}, cursor.next_object())

        self.assertEqual(
            [{'_id': 5}],
            (yield coll.find().sort([('_id', 1)])[5].to_list(100)))

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None.
        cursor = coll.find()[1000]
        self.assertFalse((yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        self.assertEqual([], (yield coll.find()[1000].to_list(100)))

    @gen_test
    def test_cursor_index_each(self):
        yield self.make_test_data()
        coll = self.collection

        results = set()
        futures = [Future() for _ in range(3)]

        def each(result, error):
            if error:
                raise error

            if result:
                results.add(result['_id'])
            else:
                futures.pop().set_result(None)

        coll.find({}, {'_id': 1}).sort([('_id', 1)])[0].each(each)
        coll.find({}, {'_id': 1}).sort([('_id', 1)])[5].each(each)

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None, which won't show up
        # in results.
        coll.find()[1000].each(each)

        yield futures
        self.assertEqual(set([0, 5]), results)

    @gen_test
    def test_rewind(self):
        yield self.collection.insert([{}, {}, {}])
        cursor = self.collection.find().limit(2)

        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1
        self.assertEqual(2, count)

        cursor.rewind()
        count = 0
        while (yield cursor.fetch_next):
            cursor.next_object()
            break

        cursor.rewind()
        while (yield cursor.fetch_next):
            cursor.next_object()
            count += 1

        self.assertEqual(2, count)
        self.assertEqual(cursor, cursor.rewind())

    @gen_test(timeout=30)
    def test_del_on_main_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        yield self.make_test_data()
        collection = self.collection
        cursor = collection.find().batch_size(1)
        yield cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(self.io_loop.add_callback)
        del cursor
        yield self.wait_for_cursor(collection, cursor_id, retrieved)

    @gen_test(timeout=30)
    def test_del_on_child_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        yield self.make_test_data()
        collection = self.collection
        cursor = [collection.find().batch_size(1)]
        yield cursor[0].fetch_next
        cursor_id = cursor[0].cursor_id
        retrieved = cursor[0].delegate._Cursor__retrieved

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(self.io_loop.add_callback)

        def f():
            # Last ref, should trigger __del__ immediately in CPython and
            # allow eventual __del__ in PyPy.
            del cursor[0]

        greenlet.greenlet(f).switch()
        yield self.wait_for_cursor(collection, cursor_id, retrieved)

    @gen_test
    def test_exhaust(self):
        if (yield server_is_mongos(self.cx)):
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

        yield self.db.drop_collection("test")

        # Insert enough documents to require more than one batch.
        yield self.db.test.insert([{} for _ in range(150)])

        client = self.motor_client(max_pool_size=1)
        # Ensure a pool.
        yield client.db.collection.find_one()
        socks = client._get_primary_pool().sockets

        # Make sure the socket is returned after exhaustion.
        cur = client[self.db.name].test.find(exhaust=True)
        has_next = yield cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))

        while (yield cur.fetch_next):
            cur.next_object()

        self.assertEqual(1, len(socks))

        # Same as previous but with to_list instead of next_object.
        docs = yield client[self.db.name].test.find(exhaust=True).to_list(None)
        self.assertEqual(1, len(socks))
        self.assertEqual(
            (yield self.db.test.count()),
            len(docs))

        # If the Cursor instance is discarded before being
        # completely iterated we have to close and
        # discard the socket.
        cur = client[self.db.name].test.find(exhaust=True).batch_size(1)
        has_next = yield cur.fetch_next
        self.assertTrue(has_next)
        self.assertEqual(0, len(socks))
        if 'PyPy' in sys.version:
            # Don't wait for GC or use gc.collect(), it's unreliable.
            cur.close()
        cur = None
        # The socket should be discarded.
        self.assertEqual(0, len(socks))


class MotorCursorMaxTimeMSTest(MotorTest):
    def setUp(self):
        super(MotorCursorMaxTimeMSTest, self).setUp()
        self.io_loop.run_sync(self.maybe_skip)

    def tearDown(self):
        self.io_loop.run_sync(self.disable_timeout)
        super(MotorCursorMaxTimeMSTest, self).tearDown()

    @gen.coroutine
    def maybe_skip(self):
        if not (yield version.at_least(self.cx, (2, 5, 3, -1))):
            raise SkipTest("maxTimeMS requires MongoDB >= 2.5.3")

        if "enableTestCommands=1" not in (yield get_command_line(self.cx)):
            raise SkipTest("testing maxTimeMS requires failpoints")

    @gen.coroutine
    def enable_timeout(self):
        yield self.cx.admin.command("configureFailPoint",
                                    "maxTimeAlwaysTimeOut",
                                    mode="alwaysOn")

    @gen.coroutine
    def disable_timeout(self):
        self.cx.admin.command("configureFailPoint",
                              "maxTimeAlwaysTimeOut",
                              mode="off")

    @gen_test
    def test_max_time_ms_query(self):
        # Cursor parses server timeout error in response to initial query.
        yield self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        with assert_raises(ExecutionTimeout):
            yield cursor.fetch_next

        cursor = self.collection.find().max_time_ms(100000)
        with assert_raises(ExecutionTimeout):
            yield cursor.to_list(10)

        with assert_raises(ExecutionTimeout):
            yield self.collection.find_one(max_time_ms=100000)

    @gen_test(timeout=60)
    def test_max_time_ms_getmore(self):
        # Cursor handles server timeout during getmore, also.
        yield self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            yield cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                while (yield cursor.fetch_next):
                    cursor.next_object()

            yield cursor.close()

            # Send another initial query.
            yield self.disable_timeout()
            cursor = self.collection.find().max_time_ms(100000)
            yield cursor.fetch_next
            cursor.next_object()

            # Test getmore timeout.
            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                yield cursor.to_list(None)

            # Avoid 'IOLoop is closing' warning.
            yield cursor.close()
        finally:
            # Cleanup.
            yield self.disable_timeout()
            yield self.collection.remove()

    @gen_test
    def test_max_time_ms_each_query(self):
        # Cursor.each() handles server timeout during initial query.
        yield self.enable_timeout()
        cursor = self.collection.find().max_time_ms(100000)
        future = Future()

        def callback(result, error):
            if error:
                future.set_exception(error)
            elif not result:
                # Done.
                future.set_result(None)

        with assert_raises(ExecutionTimeout):
            cursor.each(callback)
            yield future

    @gen_test(timeout=30)
    def test_max_time_ms_each_getmore(self):
        # Cursor.each() handles server timeout during getmore.
        yield self.collection.insert({} for _ in range(200))
        try:
            # Send initial query.
            cursor = self.collection.find().max_time_ms(100000)
            yield cursor.fetch_next
            cursor.next_object()

            future = Future()

            def callback(result, error):
                if error:
                    future.set_exception(error)
                elif not result:
                    # Done.
                    future.set_result(None)

            yield self.enable_timeout()
            with assert_raises(ExecutionTimeout):
                cursor.each(callback)
                yield future

            yield cursor.close()
        finally:
            # Cleanup.
            yield self.disable_timeout()
            yield self.collection.remove()


if __name__ == '__main__':
    unittest.main()
