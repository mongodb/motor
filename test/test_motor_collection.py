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

import unittest

import bson
from bson.objectid import ObjectId
from pymongo import ReadPreference
from pymongo.errors import DuplicateKeyError
from tornado import gen
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises, version, SkipTest
from test.utils import delay, skip_if_mongos


class MotorCollectionTest(MotorTest):
    @gen_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # MotorClient's accessors
        collection = motor.MotorCollection(self.db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        self.assertEqual('test_collection', collection.name)
        yield collection.insert({'_id': 1})
        doc = yield collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError,
            motor.MotorCollection, self.db, 'test_collection', capped=True)

    @gen_test
    def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (
                self.db.foo.bar,
                self.db.foo.bar.baz):
            yield coll.remove()
            self.assertEqual('xyzzy', (yield coll.insert({'_id': 'xyzzy'})))
            result = yield coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield coll.remove()
            self.assertEqual(None, (yield coll.find_one({'_id': 'xyzzy'})))

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.db.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @gen_test
    def test_find_is_async(self):
        # Confirm find() is async by launching two operations which will finish
        # out of order. Also test that MotorClient doesn't reuse sockets
        # incorrectly.

        # Launch find operations for _id's 1 and 2 which will finish in order
        # 2, then 1.
        coll = self.collection
        yield coll.insert([{'_id': 1}, {'_id': 2}])
        results = []

        futures = [Future(), Future()]

        def callback(result, error):
            if result:
                results.append(result)
                futures.pop().set_result(None)

        # This find() takes 0.5 seconds.
        coll.find({'_id': 1, '$where': delay(0.5)}).limit(1).each(callback)

        # Very fast lookup.
        coll.find({'_id': 2}).limit(1).each(callback)

        yield futures

        # Results were appended in order 2, 1.
        self.assertEqual([{'_id': 2}, {'_id': 1}], results)

    @gen_test
    def test_find_and_cancel(self):
        collection = self.collection
        yield collection.insert([{'_id': i} for i in range(3)])

        results = []

        future = Future()

        def callback(doc, error):
            if error:
                raise error

            results.append(doc)

            if len(results) == 2:
                future.set_result(None)
                # cancel iteration
                return False

        cursor = collection.find().sort('_id')
        cursor.each(callback)
        yield future

        # There are 3 docs, but we canceled after 2
        self.assertEqual([{'_id': 0}, {'_id': 1}], results)

        yield cursor.close()

    @gen_test(timeout=10)
    def test_find_one_is_async(self):
        # Confirm find_one() is async by launching two operations which will
        # finish out of order.
        # Launch 2 find_one operations for _id's 1 and 2, which will finish in
        # order 2 then 1.
        coll = self.collection
        yield coll.insert([{'_id': 1}, {'_id': 2}])
        results = []

        futures = [Future(), Future()]

        def callback(result, error):
            if result:
                results.append(result)
                futures.pop().set_result(None)

        # This find_one() takes 3 seconds.
        coll.find_one({'_id': 1, '$where': delay(3)}, callback=callback)

        # Very fast lookup.
        coll.find_one({'_id': 2}, callback=callback)

        yield futures

        # Results were appended in order 2, 1.
        self.assertEqual([{'_id': 2}, {'_id': 1}], results)

    @gen_test
    def test_update(self):
        yield self.collection.insert({'_id': 1})
        result = yield self.collection.update(
            {'_id': 1}, {'$set': {'foo': 'bar'}})

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result.get('err'))

    @gen_test
    def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        coll = self.db.unique_collection
        yield coll.ensure_index('s', unique=True)

        try:
            yield coll.insert([{'s': 1}, {'s': 2}])
            with assert_raises(DuplicateKeyError):
                yield coll.update({'s': 2}, {'$set': {'s': 1}})

        finally:
            yield coll.drop()

    @gen_test
    def test_update_callback(self):
        yield self.check_optional_callback(
            self.collection.update, {}, {})

    @gen_test
    def test_insert(self):
        collection = self.collection
        self.assertEqual(201, (yield collection.insert({'_id': 201})))

    @gen_test
    def test_insert_many_one_bad(self):
        collection = self.collection
        yield collection.insert({'_id': 2})

        # Violate a unique index in one of many updates, handle error.
        with assert_raises(DuplicateKeyError):
            yield collection.insert([
                {'_id': 1},
                {'_id': 2},  # Already exists
                {'_id': 3}])

        # First insert should have succeeded, but not second or third.
        self.assertEqual(
            set([1, 2]),
            set((yield collection.distinct('_id'))))

    @gen_test
    def test_save_callback(self):
        yield self.check_optional_callback(
            self.collection.save, {})

    @gen_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5.
        self.assertEqual(
            5,
            (yield self.collection.save({'_id': 5})))

    @gen_test
    def test_save_without_id(self):
        collection = self.collection
        result = yield collection.save({'fiddle': 'faddle'})

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))

    @gen_test
    def test_save_bad(self):
        coll = self.db.unique_collection
        yield coll.ensure_index('s', unique=True)
        yield coll.save({'s': 1})

        try:
            with assert_raises(DuplicateKeyError):
                yield coll.save({'s': 1})
        finally:
            yield coll.drop()

    @gen_test
    def test_remove(self):
        # Remove a document twice, check that we get a success response first
        # time and an error the second time.
        yield self.collection.insert({'_id': 1})
        result = yield self.collection.remove({'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

        result = yield self.collection.remove({'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

    @gen_test
    def test_remove_callback(self):
        yield self.check_optional_callback(self.collection.remove)

    @gen_test
    def test_unacknowledged_remove(self):
        coll = self.collection
        yield coll.remove()
        yield coll.insert([{'_id': i} for i in range(3)])

        # Don't yield the futures.
        coll.remove({'_id': 0})
        coll.remove({'_id': 1})
        coll.remove({'_id': 2})

        # Wait for them to complete
        while (yield coll.count()):
            yield self.pause(0.1)

        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_insert(self):
        # Test that unsafe inserts with no callback still work

        # Insert id 1 without a callback or w=1.
        coll = self.db.test_unacknowledged_insert
        coll.insert({'_id': 1})

        # The insert is eventually executed.
        while not (yield coll.count()):
            yield self.pause(0.1)

        # DuplicateKeyError not raised.
        future = coll.insert({'_id': 1})
        yield coll.insert({'_id': 1}, w=0)

        with assert_raises(DuplicateKeyError):
            yield future

    @gen_test
    def test_unacknowledged_save(self):
        # Test that unsafe saves with no callback still work
        collection_name = 'test_unacknowledged_save'
        coll = self.db[collection_name]
        coll.save({'_id': 201})

        while not (yield coll.find_one({'_id': 201})):
            yield self.pause(0.1)

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield coll.save({'_id': 201}, w=0)
        coll.database.connection.close()

    @gen_test
    def test_unacknowledged_update(self):
        # Test that unsafe updates with no callback still work
        coll = self.collection

        yield coll.insert({'_id': 1})
        coll.update({'_id': 1}, {'$set': {'a': 1}})

        while not (yield coll.find_one({'a': 1})):
            yield self.pause(0.1)

        coll.database.connection.close()

    @gen_test
    def test_nested_callbacks(self):
        results = [0]
        future = Future()
        yield self.collection.insert({'_id': 1})

        def callback(result, error):
            if error:
                raise error

            if not result:
                # Done iterating
                return

            results[0] += 1
            if results[0] < 1000:
                self.collection.find({'_id': 1}).each(callback)
            else:
                future.set_result(None)

        self.collection.find({'_id': 1}).each(callback)

        yield future
        self.assertEqual(1000, results[0])

    @gen_test
    def test_map_reduce(self):
        # Count number of documents with even and odd _id
        yield self.make_test_data()
        expected_result = [{'_id': 0, 'value': 100}, {'_id': 1, 'value': 100}]
        map_fn = bson.Code('function map() { emit(this._id % 2, 1); }')
        reduce_fn = bson.Code('''
        function reduce(key, values) {
            r = 0;
            values.forEach(function(value) { r += value; });
            return r;
        }''')

        yield self.db.tmp_mr.drop()

        # First do a standard mapreduce, should return MotorCollection
        collection = self.collection
        tmp_mr = yield collection.map_reduce(map_fn, reduce_fn, 'tmp_mr')

        self.assertTrue(
            isinstance(tmp_mr, motor.MotorCollection),
            'map_reduce should return MotorCollection, not %s' % tmp_mr)

        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Standard mapreduce with full response
        yield self.db.tmp_mr.drop()
        response = yield collection.map_reduce(
            map_fn, reduce_fn, 'tmp_mr', full_response=True)

        self.assertTrue(
            isinstance(response, dict),
            'map_reduce should return dict, not %s' % response)

        self.assertEqual('tmp_mr', response['result'])
        result = yield tmp_mr.find().sort([('_id', 1)]).to_list(length=1000)
        self.assertEqual(expected_result, result)

        # Inline mapreduce
        yield self.db.tmp_mr.drop()
        result = yield collection.inline_map_reduce(
            map_fn, reduce_fn)

        result.sort(key=lambda doc: doc['_id'])
        self.assertEqual(expected_result, result)

    @gen_test
    def test_indexes(self):
        test_collection = self.collection

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

    @gen_test
    def test_aggregation_cursor(self):
        if not (yield version.at_least(self.cx, (2, 5, 1))):
            raise SkipTest("Aggregation cursor requires MongoDB >= 2.5.1")

        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            yield db.drop_collection("test")
            yield db.test.insert([{'_id': i} for i in range(collection_size)])
            expected_sum = sum(range(collection_size))
            cursor = yield db.test.aggregate(
                {'$project': {'_id': '$_id'}}, cursor={})

            docs = yield cursor.to_list(collection_size)
            self.assertEqual(
                expected_sum,
                sum(doc['_id'] for doc in docs))

    @gen_test(timeout=30)
    def test_parallel_scan(self):
        if not (yield version.at_least(self.cx, (2, 5, 5))):
            raise SkipTest("Requires MongoDB >= 2.5.5")

        yield skip_if_mongos(self.cx)

        collection = self.collection

        # Enough documents that each cursor requires multiple batches.
        yield collection.remove()
        yield collection.insert(({'_id': i} for i in range(8000)), w=test.env.w)
        if test.env.is_replica_set:
            client = self.motor_rsc()

            # Test that getMore messages are sent to the right server.
            client.read_preference = ReadPreference.SECONDARY
            collection = client.motor_test.test_collection

        docs = []

        @gen.coroutine
        def f(cursor):
            self.assertTrue(isinstance(cursor, motor.MotorCommandCursor))

            while (yield cursor.fetch_next):
                docs.append(cursor.next_object())

        cursors = yield collection.parallel_scan(3)
        yield [f(cursor) for cursor in cursors]
        self.assertEqual(len(docs), (yield collection.count()))

if __name__ == '__main__':
    unittest.main()
