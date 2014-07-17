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

"""Test MotorCursor with asyncio."""

import unittest
from asyncio import Future

import greenlet
from pymongo.errors import OperationFailure

from test.asyncio_tests import asyncio_test, AsyncIOTestCase


class TestAsyncIOCursor(AsyncIOTestCase):
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

    @asyncio_test
    def test_fetch_next_delete(self):
        coll = self.collection
        yield from coll.insert({})

        # Decref'ing the cursor eventually closes it on the server.
        cursor = coll.find()
        yield from cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved
        del cursor
        yield from self.wait_for_cursor(coll, cursor_id, retrieved)

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
    def test_fetch_next_exception(self):
        coll = self.collection
        cursor = coll.find()
        cursor.delegate._Cursor__id = 1234  # Not valid on server.

        with self.assertRaises(OperationFailure):
            yield from cursor.fetch_next

        # Avoid the cursor trying to close itself when it goes out of scope.
        cursor.delegate._Cursor__id = None

    @asyncio_test
    def test_each(self):
        yield from self.make_test_data()
        cursor = self.collection.find({}, {'_id': 1}).sort('_id')
        future = Future(loop=self.loop)
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
    def test_to_list_with_length(self):
        yield from self.make_test_data()
        coll = self.collection
        cursor = coll.find().sort('_id')

        def expected(start, stop):
            return [{'_id': i} for i in range(start, stop)]

        self.assertEqual(expected(0, 10), (yield from cursor.to_list(10)))
        self.assertEqual(expected(10, 100), (yield from cursor.to_list(90)))
        yield from cursor.close()

    @asyncio_test
    def test_cursor_explicit_close(self):
        yield from self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        yield from cursor.fetch_next
        self.assertTrue(cursor.alive)
        yield from cursor.close()

        # Cursor reports it's alive because it has buffered data, even though
        # it's killed on the server
        self.assertTrue(cursor.alive)
        retrieved = cursor.delegate._Cursor__retrieved
        yield from self.wait_for_cursor(collection, cursor.cursor_id, retrieved)

    @asyncio_test
    def test_del_on_main_greenlet(self):
        # Since __del__ can happen on any greenlet, cursor must be
        # prepared to close itself correctly on main or a child.
        yield from self.make_test_data()
        collection = self.collection
        cursor = collection.find()
        yield from cursor.fetch_next
        cursor_id = cursor.cursor_id
        retrieved = cursor.delegate._Cursor__retrieved
        del cursor
        yield from self.wait_for_cursor(collection, cursor_id, retrieved)

    @asyncio_test
    def test_del_on_child_greenlet(self):
        # Since __del__ can happen on any greenlet, cursor must be
        # prepared to close itself correctly on main or a child.
        yield from self.make_test_data()
        collection = self.collection
        cursor = [collection.find().batch_size(1)]
        yield from cursor[0].fetch_next
        cursor_id = cursor[0].cursor_id
        retrieved = cursor[0].delegate._Cursor__retrieved

        def f():
            # Last ref, should trigger __del__ immediately in CPython and
            # allow eventual __del__ in PyPy.
            del cursor[0]
            return

        greenlet.greenlet(f).switch()
        yield from self.wait_for_cursor(collection, cursor_id, retrieved)


if __name__ == '__main__':
    unittest.main()
