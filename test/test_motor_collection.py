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
import unittest

import bson
from tornado import gen
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError
from test.utils import delay
from tornado.testing import gen_test

import motor
from test import MotorTest, AssertEqual, assert_raises


class MotorCollectionTest(MotorTest):
    @gen_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # MotorClient's accessors
        db = self.cx.pymongo_test
        collection = motor.MotorCollection(db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        doc = yield collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

    @gen_test
    def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (
                self.cx.pymongo_test.foo.bar,
                self.cx.pymongo_test.foo.bar.baz):
            yield coll.remove()
            self.assertEqual('xyzzy', (yield coll.insert({'_id': 'xyzzy'})))
            result = yield coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield coll.remove()
            self.assertEqual(None, (yield coll.find_one({'_id': 'xyzzy'})))

    @gen_test
    def test_find_is_async(self):
        # Confirm find() is async by launching two operations which will finish
        # out of order. Also test that MotorClient doesn't reuse sockets
        # incorrectly.

        # Launch find operations for _id's 1 and 2 which will finish in order
        # 2, then 1.
        results = []

        yield_points = [(yield gen.Callback(0)), (yield gen.Callback(1))]

        def callback(result, error):
            if result:
                results.append(result)
                yield_points.pop()()

        # This find() takes 0.5 seconds
        self.cx.pymongo_test.test_collection.find(
            {'_id': 1, '$where': delay(0.5)},
            fields={'s': True, '_id': False}
        ).limit(1).each(callback)

        # Very fast lookup
        self.cx.pymongo_test.test_collection.find(
            {'_id': 2},
            fields={'s': True, '_id': False}
        ).limit(1).each(callback)

        yield gen.WaitAll([0, 1])

        # Results were appended in order 2, 1
        self.assertEqual(
            [{'s': hex(s)} for s in (2, 1)],
            results)

    @gen_test
    def test_find_and_cancel(self):
        results = []

        yield_point = yield gen.Callback(0)

        def callback(doc, error):
            if error:
                raise error

            results.append(doc)

            if len(results) == 2:
                yield_point()
                # cancel iteration
                return False

        cursor = self.cx.pymongo_test.test_collection.find(sort=[('s', 1)])
        cursor.each(callback)
        yield gen.Wait(0)

        # There are 200 docs, but we canceled after 2
        self.assertEqual(
            [{'_id': 0, 's': hex(0)}, {'_id': 1, 's': hex(1)}], results)

        yield cursor.close()

    @gen_test
    def test_find_one(self):
        self.assertEqual(
            {'_id': 1, 's': hex(1)},
            (yield self.cx.pymongo_test.test_collection.find_one({'_id': 1})))

    @gen_test
    def test_find_one_is_async(self):
        # Confirm find_one() is async by launching two operations which will
        # finish out of order.
        # Launch 2 find_one operations for _id's 1 and 2, which will finish in
        # order 2 then 1.
        results = []

        yield_points = [(yield gen.Callback(0)), (yield gen.Callback(1))]

        def callback(result, error):
            if result:
                results.append(result)
                yield_points.pop()()

        # This find_one() takes 3 seconds
        self.cx.pymongo_test.test_collection.find_one(
            {'_id': 1, '$where': delay(3)},
            fields={'s': True, '_id': False},
            callback=callback)

        # Very fast lookup
        self.cx.pymongo_test.test_collection.find_one(
            {'_id': 2},
            fields={'s': True, '_id': False},
            callback=callback)

        yield gen.WaitAll([0, 1])

        # Results were appended in order 2, 1
        self.assertEqual([{'s': hex(s)} for s in (2, 1)], results)

    @gen_test
    def test_update(self):
        result = yield self.cx.pymongo_test.test_collection.update(
            {'_id': 5}, {'$set': {'foo': 'bar'}})

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result['err'])

    @gen_test
    def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        # There's already a document with s: hex(4)
        with assert_raises(DuplicateKeyError):
            yield self.cx.pymongo_test.test_collection.update(
                {'_id': 5}, {'$set': {'s': hex(4)}})

    @gen_test
    def test_update_callback(self):
        yield self.check_optional_callback(
            self.cx.pymongo_test.test_collection.update, {}, {})

    @gen_test
    def test_insert(self):
        collection = self.cx.pymongo_test.test_collection
        self.assertEqual(201, (yield collection.insert({'_id': 201})))

    @gen_test
    def test_insert_many(self):
        yield AssertEqual(
            range(201, 211),
            self.cx.pymongo_test.test_collection.insert,
            [{'_id': i, 's': hex(i)} for i in range(201, 211)])

    @gen_test
    def test_insert_bad(self):
        # Violate a unique index, make sure we handle error well
        with assert_raises(DuplicateKeyError):
            # There's already a document with s: hex(4)
            yield self.cx.pymongo_test.test_collection.insert({'s': hex(4)})

    def test_insert_many_one_bad(self):
        # Violate a unique index in one of many updates, handle error.
        with assert_raises(DuplicateKeyError):
            yield self.cx.pymongo_test.test_collection.insert([
                {'_id': 201, 's': hex(201)},
                {'_id': 202, 's': hex(4)},  # Already exists
                {'_id': 203, 's': hex(203)}])

        # First insert should have succeeded.
        yield AssertEqual(
            [{'_id': 201, 's': hex(201)}],
            self.sync_db.test_collection.find({'_id': 201}).to_list,
            length=1000)

        # Final insert didn't execute, since second failed.
        yield AssertEqual(
            [],
            self.sync_db.test_collection.find({'_id': 203}).to_list,
            length=1000)

    @gen_test
    def test_save_callback(self):
        yield self.check_optional_callback(
            self.cx.pymongo_test.test_collection.save, {})

    @gen_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5
        yield AssertEqual(
            5,
            self.cx.pymongo_test.test_collection.save,
            {'_id': 5})

    @gen_test
    def test_save_without_id(self):
        result = yield self.cx.pymongo_test.test_collection.save({'fiddle': 'faddle'})

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))

    @gen_test
    def test_save_bad(self):
        # Violate a unique index, make sure we handle error well
        collection = self.cx.pymongo_test.test_collection
        with assert_raises(DuplicateKeyError):
            # There's already a document with s: hex(4).
            yield collection.save({'_id': 5, 's': hex(4)})

        collection.database.connection.close()

    @gen_test
    def test_remove(self):
        # Remove a document twice, check that we get a success response first
        # time and an error the second time.
        result = yield self.cx.pymongo_test.test_collection.remove({'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result['err'])

        result = yield self.cx.pymongo_test.test_collection.remove({'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result['err'])

    @gen_test
    def test_remove_callback(self):
        yield self.check_optional_callback(
            self.cx.pymongo_test.test_collection.remove)

    @gen_test
    def test_unacknowledged_remove(self):
        # Test that unsafe removes with no callback still work
        def ndocs():
            return self.sync_coll.find(
                {'_id': {'$gte': 115, '$lte': 117}}).count()

        self.assertEqual(3, ndocs(), msg="Test setup should have 3 documents")
        coll = self.cx.pymongo_test.test_collection
        # Unacknowledged removes
        coll.remove({'_id': 115})
        coll.remove({'_id': 116})
        coll.remove({'_id': 117})
        # Wait for them to complete
        loop = self.io_loop
        while ndocs():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_insert(self):
        # Test that unsafe inserts with no callback still work

        # id 201 not present
        self.assertEqual(0, self.sync_coll.find({'_id': 201}).count())

        # insert id 201 without a callback or w=1
        coll = self.cx.pymongo_test.test_collection
        coll.insert({'_id': 201})

        # the insert is eventually executed
        loop = self.io_loop
        while not self.sync_db.test_collection.find({'_id': 201}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        # DuplicateKeyError not raised
        coll.insert({'_id': 201})
        yield coll.insert({'_id': 201}, w=0)
        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_save(self):
        # Test that unsafe saves with no callback still work
        coll = self.cx.pymongo_test.test_collection
        coll.save({'_id': 201})

        loop = self.io_loop
        while not self.sync_db.test_collection.find({'_id': 201}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield coll.save({'_id': 201}, w=0)
        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_update(self):
        # Test that unsafe updates with no callback still work
        coll = self.cx.pymongo_test.test_collection
        coll.update({'_id': 100}, {'$set': {'a': 1}})

        loop = self.io_loop
        while not self.sync_db.test_collection.find({'a': 1}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        coll.database.connection.close()

    @gen_test
    def test_nested_callbacks(self):
        results = [0]
        yield_point = yield gen.Callback(0)

        def callback(result, error):
            if error:
                raise error

            if not result:
                # Done iterating
                return

            results[0] += 1
            if results[0] < 1000:
                self.cx.pymongo_test.test_collection.find(
                    {'_id': 1},
                    {'s': False},
                ).each(callback)
            else:
                yield_point()

        self.cx.pymongo_test.test_collection.find(
            {'_id': 1},
            {'s': False},
        ).each(callback)

        yield gen.Wait(0)

        self.assertEqual(
            1000,
            results[0])

    @gen_test
    def test_map_reduce(self):
        # Count number of documents with even and odd _id
        expected_result = [{'_id': 0, 'value': 100}, {'_id': 1, 'value': 100}]
        map_fn = bson.Code('function map() { emit(this._id % 2, 1); }')
        reduce_fn = bson.Code('''
        function reduce(key, values) {
            r = 0;
            values.forEach(function(value) { r += value; });
            return r;
        }''')

        yield self.cx.pymongo_test.tmp_mr.drop()

        # First do a standard mapreduce, should return MotorCollection
        collection = self.cx.pymongo_test.test_collection
        tmp_mr = yield collection.map_reduce(map_fn, reduce_fn, 'tmp_mr')

        self.assertTrue(
            isinstance(tmp_mr, motor.MotorCollection),
            'map_reduce should return MotorCollection, not %s' % tmp_mr)

        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Standard mapreduce with full response
        yield self.cx.pymongo_test.tmp_mr.drop()
        response = yield collection.map_reduce(
            map_fn, reduce_fn, 'tmp_mr', full_response=True)

        self.assertTrue(
            isinstance(response, dict),
            'map_reduce should return dict, not %s' % response)

        self.assertEqual('tmp_mr', response['result'])
        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Inline mapreduce
        yield self.cx.pymongo_test.tmp_mr.drop()
        result = yield collection.inline_map_reduce(
            map_fn, reduce_fn)

        result.sort(key=lambda doc: doc['_id'])
        self.assertEqual(expected_result, result)

    @gen_test
    def test_indexes(self):
        test_collection = self.cx.pymongo_test.test_collection

        # Create an index
        idx_name = yield test_collection.create_index([('foo', 1)])
        index_info = yield test_collection.index_information()
        self.assertEqual([('foo', 1)], index_info[idx_name]['key'])

        # Ensure the same index, test that callback is executed
        result = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result)
        result2 = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result2)

        # Ensure an index that doesn't exist, test it's created
        yield test_collection.ensure_index([('bar', 1)])
        index_info = yield test_collection.index_information()
        self.assertTrue(any([
            info['key'] == [('bar', 1)] for info in index_info.values()]))

        # Don't test drop_index or drop_indexes -- Synchro tests them


if __name__ == '__main__':
    unittest.main()
