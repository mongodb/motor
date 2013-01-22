# Copyright 2012 10gen, Inc.
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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import datetime
import os
import time
import unittest
from functools import partial

import greenlet
import pymongo
from tornado import ioloop, gen
from pymongo.errors import InvalidOperation, ConfigurationError

import motor
from test import host, port, MotorTest, async_test_engine, AssertEqual


class MotorCursorTest(MotorTest):
    @gen.engine
    def wait_for_cursors(self, callback):
        """Ensure any cursors opened during the test have been closed on the
        server. `yield motor.Op(cursor.close)` is usually simpler.
        """
        timeout_sec = float(os.environ.get('TIMEOUT_SEC', 5)) - 1
        loop = ioloop.IOLoop.instance()
        start = time.time()
        while self.get_open_cursors() > self.open_cursors:
            if time.time() - start > timeout_sec:
                self.fail("Waited too long for cursors to close")

            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        callback()

    def test_cursor(self):
        cx = self.motor_connection(host, port)
        coll = cx.pymongo_test.test_collection
        cursor = coll.find()
        self.assertTrue(isinstance(cursor, motor.MotorCursor))
        self.assertFalse(cursor.started, "Cursor shouldn't start immediately")

    @async_test_engine()
    def test_count(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        yield AssertEqual(200, coll.find().count)
        yield AssertEqual(100, coll.find({'_id': {'$gt': 99}}).count)
        where = 'this._id % 2 == 0 && this._id >= 50'
        yield AssertEqual(75, coll.find({'$where': where}).count)
        yield AssertEqual(75, coll.find().where(where).count)
        yield AssertEqual(
            25,
            coll.find({'_id': {'$lt': 100}}).where(where).count)
        yield AssertEqual(
            25,
            coll.find({'_id': {'$lt': 100}, '$where': where}).count)
        done()

    @async_test_engine()
    def test_distinct(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        self.assertEqual(set(range(10)), set((
            yield motor.Op(coll.find({'_id': {'$lt': 10}}).distinct, '_id'))))
        done()

    @async_test_engine()
    def test_fetch_next(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        # 200 results, only including _id field, sorted by _id
        cursor = coll.find({}, {'_id': 1}).sort(
            [('_id', pymongo.ASCENDING)]).batch_size(75)

        self.assertEqual(None, cursor.cursor_id)
        self.assertEqual(None, cursor.next_object()) # Haven't fetched yet
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

        # Decref'ing the cursor eventually closes it on the server; yielding
        # clears the engine Runner's reference to the cursor.
        cursor = coll.find()
        yield cursor.fetch_next
        del cursor
        yield gen.Task(ioloop.IOLoop.instance().add_callback)
        yield gen.Task(self.wait_for_cursors)
        done()

    @async_test_engine()
    def test_fetch_next_without_results(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        # Nothing matches this query
        cursor = coll.find({'foo':'bar'})
        self.assertEqual(None, cursor.next_object())
        self.assertEqual(False, (yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())
        # Now cursor knows it's exhausted
        self.assertEqual(0, cursor.cursor_id)
        done()

    @async_test_engine()
    def test_fetch_next_is_idempotent(self, done):
        # Subsequent calls to fetch_next don't do anything
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find()
        self.assertEqual(None, cursor.cursor_id)
        yield cursor.fetch_next
        self.assertTrue(cursor.cursor_id)
        self.assertEqual(101, cursor.buffer_size)
        yield cursor.fetch_next # Does nothing
        self.assertEqual(101, cursor.buffer_size)
        done()

    @async_test_engine()
    def test_each(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find({}, {'_id': 1}).sort([('_id', pymongo.ASCENDING)])
        yield_point = yield gen.Callback(0)
        results = []
        def callback(result, error):
            if error:
                raise error

            results.append(result)
            if not result:
                yield_point()

        cursor.each(callback)
        yield gen.Wait(0)
        expected = [{'_id': i} for i in range(200)] + [None]
        self.assertEqual(expected, results)
        done()

    def test_to_list_argument_checking(self):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find()
        self.check_callback_handling(partial(cursor.to_list, 10), True)

        cursor = coll.find()
        callback = lambda result, error: None
        self.assertRaises(ConfigurationError, cursor.to_list, -1, callback)
        self.assertRaises(ConfigurationError, cursor.to_list, 'foo', callback)

    @async_test_engine()
    def test_to_list(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find({}, {'_id': 1}).sort([('_id', pymongo.ASCENDING)])
        expected = [{'_id': i} for i in range(200)]
        yield AssertEqual(expected, cursor.to_list)
        yield motor.Op(cursor.close)
        done()

    @async_test_engine()
    def test_to_list_with_length(self, done):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find({}, {'_id': 1}).sort([('_id', pymongo.ASCENDING)])
        yield AssertEqual([], cursor.to_list, 0)

        def expected(start, stop):
            return [{'_id': i} for i in range(start, stop)]

        yield AssertEqual(expected(0, 10), cursor.to_list, 10)
        yield AssertEqual(expected(10, 100), cursor.to_list, 90)

        # Test particularly rigorously around the 101-doc mark, since this is
        # where the first batch ends
        yield AssertEqual(expected(100, 101), cursor.to_list, 1)
        yield AssertEqual(expected(101, 102), cursor.to_list, 1)
        yield AssertEqual(expected(102, 103), cursor.to_list, 1)
        yield AssertEqual([], cursor.to_list, 0)
        yield AssertEqual(expected(103, 105), cursor.to_list, 2)

        # Only 95 docs left, make sure length=100 doesn't error or hang
        yield AssertEqual(expected(105, 200), cursor.to_list, 100)
        self.assertEqual(0, cursor.cursor_id)

        # Check that passing None explicitly is the same as no length
        result = yield motor.Op(coll.find().to_list, None)
        self.assertEqual(200, len(result))
        done()

    def test_to_list_tailable(self):
        coll = self.motor_connection(host, port).pymongo_test.test_collection
        cursor = coll.find(tailable=True)

        # Can't call to_list on tailable cursor
        self.assertRaises(
            InvalidOperation, cursor.to_list, callback=lambda: None)

    @async_test_engine()
    def test_limit_zero(self, done):
        # Limit of 0 is a weird case that PyMongo handles specially, make sure
        # Motor does too. cursor.limit(0) means "remove limit", but cursor[:0]
        # or cursor[5:5] sets the cursor to "empty".
        coll = self.motor_connection(host, port).pymongo_test.test_collection

        # Make sure our setup code made some documents
        results = yield motor.Op(coll.find().to_list)
        self.assertTrue(len(results) > 0)
        self.assertEqual(False, (yield coll.find()[:0].fetch_next))
        self.assertEqual(False, (yield coll.find()[5:5].fetch_next))
        yield AssertEqual(None, coll.find()[:0].each)
        yield AssertEqual(None, coll.find()[5:5].each)
        yield AssertEqual([], coll.find()[:0].to_list)
        yield AssertEqual([], coll.find()[5:5].to_list)
        done()

    @async_test_engine()
    def test_cursor_explicit_close(self, done):
        cx = self.motor_connection(host, port)
        cursor = cx.pymongo_test.test_collection.find()
        yield cursor.fetch_next
        self.assertTrue(cursor.alive)
        yield motor.Op(cursor.close)

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server
        self.assertTrue(cursor.alive)
        yield gen.Task(self.wait_for_cursors)
        done()

    @async_test_engine()
    def test_each(self, done):
        # 1. Open a connection.
        #
        # 2. test_collection has docs inserted in setUp(). Query for documents
        # with _id 0 through 13, in batches of 5: 0-4, 5-9, 10-13.
        #
        # 3. For each document, check if the cursor has been closed. I expect
        # it to remain open until we've retrieved doc with _id 10. Oddly, Mongo
        # doesn't close the cursor and return cursor_id 0 if the final batch
        # exactly contains the last document -- the last batch size has to go
        # at least one *past* the final document in order to close the cursor.
        connection = self.motor_connection(host, port)

        cursor = connection.pymongo_test.test_collection.find(
            {'_id': {'$lt':14}},
            {'s': False}, # exclude 's' field
            sort=[('_id', 1)],
        ).batch_size(5)

        each_done = yield gen.Callback('each_done')

        def callback(doc, error):
            if error:
                raise error

            if doc:
                results.append(doc['_id'])

            if doc and doc['_id'] < 10:
                self.assertEqual(
                    1 + self.open_cursors,
                    self.get_open_cursors()
                )
            else:
                self.assertEqual(
                    self.open_cursors,
                    self.get_open_cursors()
                )

            if not doc:
                # Done
                each_done()

        results = []
        cursor.each(callback)
        yield gen.Wait('each_done')
        self.assertEqual(range(14), results)
        done()

    def test_each_cancel(self):
        loop = ioloop.IOLoop.instance()
        cx = self.motor_connection(host, port)
        collection = cx.pymongo_test.test_collection
        results = []

        def cancel(result, error):
            if error:
                loop.stop()
                raise error

            results.append(result)
            loop.add_callback(canceled)
            return False # Cancel iteration

        def canceled():
            try:
                self.assertFalse(cursor.delegate._Cursor__killed)
                self.assertTrue(cursor.alive)

                # Resume iteration
                cursor.each(each)
            except Exception:
                loop.stop()
                raise

        def each(result, error):
            if error:
                loop.stop()
                raise error

            if result:
                results.append(result)
            else:
                # Complete
                loop.stop()

        cursor = collection.find()
        cursor.each(cancel)
        loop.start()

        self.assertEqual(self.sync_coll.count(), len(results))

    def test_cursor_slice_argument_checking(self):
        cx = self.motor_connection(host, port)
        collection = cx.pymongo_test.test_collection

        for arg in '', None, {}, []:
            self.assertRaises(TypeError, lambda: collection.find()[arg])

        self.assertRaises(IndexError, lambda: collection.find()[-1])

    @async_test_engine()
    def test_cursor_slice(self, done):
        # This is an asynchronous copy of PyMongo's test_getitem_slice_index in
        # test_cursor.py

        cx = self.motor_connection(host, port)

        # test_collection was filled out in setUp()
        coll = cx.pymongo_test.test_collection

        self.assertRaises(IndexError, lambda: coll.find()[-1])
        self.assertRaises(IndexError, lambda: coll.find()[1:2:2])
        self.assertRaises(IndexError, lambda: coll.find()[2:1])

        result = yield motor.Op(coll.find()[0:].to_list)
        self.assertEqual(200, len(result))

        result = yield motor.Op(coll.find()[20:].to_list)
        self.assertEqual(180, len(result))

        result = yield motor.Op(coll.find()[99:].to_list)
        self.assertEqual(101, len(result))

        result = yield motor.Op(coll.find()[1000:].to_list)
        self.assertEqual(0, len(result))

        result = yield motor.Op(coll.find()[20:25].to_list)
        self.assertEqual(5, len(result))

        # Any slice overrides all previous slices
        result = yield motor.Op(coll.find()[20:25][20:].to_list)
        self.assertEqual(180, len(result))

        result = yield motor.Op(coll.find()[20:25].limit(0).skip(20).to_list)
        self.assertEqual(180, len(result))

        result = yield motor.Op(coll.find().limit(0).skip(20)[20:25].to_list)
        self.assertEqual(5, len(result))

        result = yield motor.Op(coll.find()[:1].to_list)
        self.assertEqual(1, len(result))

        result = yield motor.Op(coll.find()[:5].to_list)
        self.assertEqual(5, len(result))

        done()

    @async_test_engine()
    def test_cursor_index(self, done):
        cx = self.motor_connection(host, port)

        # test_collection was filled out in setUp() with 200 docs
        coll = cx.pymongo_test.test_collection
        cursor = coll.find().sort([('_id', 1)])[0]
        yield cursor.fetch_next
        self.assertEqual({'_id': 0, 's': hex(0)}, cursor.next_object())

        yield AssertEqual(
            [{'_id': 5, 's': hex(5)}],
            coll.find().sort([('_id', 1)])[5].to_list)

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None.
        cursor = coll.find()[1000]
        yield cursor.fetch_next
        self.assertEqual(None, cursor.next_object())
        yield AssertEqual([], coll.find()[1000].to_list)
        done()

    @async_test_engine()
    def test_cursor_index_each(self, done):
        cx = self.motor_connection(host, port)

        # test_collection was filled out in setUp() with 200 docs
        coll = cx.pymongo_test.test_collection

        results = []
        yield_points = [(yield gen.Callback(i)) for i in range(3)]

        def each(result, error):
            if error:
                raise error

            if result:
                results.append(result)
            else:
                yield_points.pop()()

        coll.find({}, {'_id': 1}).sort([('_id', 1)])[0].each(each)
        coll.find({}, {'_id': 1}).sort([('_id', 1)])[5].each(each)

        # Only 200 documents, so 1000th doc doesn't exist. PyMongo raises
        # IndexError here, but Motor simply returns None, which won't show up
        # in results.
        coll.find()[1000].each(each)

        yield gen.WaitAll(range(3))
        self.assertEqual([{'_id': 0}, {'_id': 5}], sorted(results))
        done()

    @async_test_engine()
    def test_rewind(self, done):
        cx = self.motor_connection(host, port)
        cursor = cx.pymongo_test.test_collection.find().limit(2)

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
        done()

    @async_test_engine()
    def test_del_on_main_greenlet(self, done):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        cx = self.motor_connection(host, port)
        cursor = cx.pymongo_test.test_collection.find()
        yield cursor.fetch_next
        self.assertEqual(1 + self.open_cursors, self.get_open_cursors())

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(ioloop.IOLoop.instance().add_callback)
        self.assertEqual(1 + self.open_cursors, self.get_open_cursors())

        del cursor
        yield gen.Task(self.wait_for_cursors)
        done()

    @async_test_engine()
    def test_del_on_child_greenlet(self, done):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        cx = self.motor_connection(host, port)
        cursor = [cx.pymongo_test.test_collection.find()]
        yield cursor[0].fetch_next

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(ioloop.IOLoop.instance().add_callback)
        self.assertEqual(1 + self.open_cursors, self.get_open_cursors())

        def f():
            # Last ref, should trigger __del__ immediately in CPython and
            # allow eventual __del__ in PyPy.
            del cursor[0]

        greenlet.greenlet(f).switch()
        yield gen.Task(self.wait_for_cursors)
        done()


if __name__ == '__main__':
    unittest.main()
