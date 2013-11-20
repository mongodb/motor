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

import unittest

import greenlet
import pymongo
from tornado import gen
from pymongo.errors import InvalidOperation, ConfigurationError
from pymongo.errors import OperationFailure
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises


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
        self.make_test_data()
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
        self.make_test_data()
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

    @gen_test
    def test_fetch_next_delete(self):
        coll = self.collection
        yield coll.insert({})

        # Decref'ing the cursor eventually closes it on the server; yielding
        # clears the engine Runner's reference to the cursor.
        cursor = coll.find()
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
        self.make_test_data()
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
        yield self.check_required_callback(self.collection.find().each)

    @gen_test
    def test_each(self):
        self.make_test_data()
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
        coll = self.collection
        cursor = coll.find()
        yield self.check_optional_callback(cursor.to_list, 10)
        cursor = coll.find()
        callback = lambda result, error: None
        self.assertRaises(ConfigurationError, cursor.to_list, -1, callback)
        self.assertRaises(ConfigurationError, cursor.to_list, 'foo', callback)
        self.assertRaises(TypeError, cursor.to_list, None, callback)

    @gen_test
    def test_to_list_callback(self):
        self.make_test_data()
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
        self.make_test_data()
        coll = self.collection
        cursor = coll.find({}, {'_id': 1}).sort([('_id', pymongo.ASCENDING)])
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

    def test_to_list_tailable(self):
        coll = self.collection
        cursor = coll.find(tailable=True)

        # Can't call to_list on tailable cursor
        self.assertRaises(
            InvalidOperation,
            cursor.to_list, length=10, callback=lambda result, error: None)

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

    @gen_test
    def test_cursor_explicit_close(self):
        self.make_test_data()
        collection = self.collection
        yield self.check_optional_callback(collection.find().close)
        cursor = collection.find()
        yield cursor.fetch_next
        self.assertTrue(cursor.alive)
        yield cursor.close()

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server
        self.assertTrue(cursor.alive)
        retrieved = cursor.delegate._Cursor__retrieved
        yield self.wait_for_cursor(collection, cursor.cursor_id, retrieved)

    def test_each_cancel(self):
        self.make_test_data()
        loop = self.io_loop
        collection = self.collection
        results = []

        def cancel(result, error):
            if error:
                loop.stop()
                raise error

            results.append(result)
            loop.add_callback(canceled)
            return False  # Cancel iteration.

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

        self.assertEqual(test.sync_collection.count(), len(results))

    def test_cursor_slice_argument_checking(self):
        collection = self.collection

        for arg in '', None, {}, []:
            self.assertRaises(TypeError, lambda: collection.find()[arg])

        self.assertRaises(IndexError, lambda: collection.find()[-1])

    @gen_test
    def test_cursor_slice(self):
        # This is an asynchronous copy of PyMongo's test_getitem_slice_index in
        # test_cursor.py

        self.make_test_data()
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

    @gen_test
    def test_cursor_index(self):
        self.make_test_data()
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
        self.make_test_data()
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

    @gen_test
    def test_del_on_main_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        yield cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved

        # Clear the FetchNext reference from this gen.Runner so it's deleted
        # and decrefs the cursor
        yield gen.Task(self.io_loop.add_callback)
        del cursor
        yield self.wait_for_cursor(collection, cursor_id, retrieved)

    @gen_test
    def test_del_on_child_greenlet(self):
        # Since __del__ can happen on any greenlet, MotorCursor must be
        # prepared to close itself correctly on main or a child.
        self.make_test_data()
        collection = self.collection
        cursor = [collection.find()]
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


if __name__ == '__main__':
    unittest.main()
