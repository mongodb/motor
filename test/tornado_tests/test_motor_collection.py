# Copyright 2012-2015 MongoDB, Inc.
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

import sys
import traceback
import unittest

import bson
from bson import CodecOptions
from bson.binary import JAVA_LEGACY
from bson.objectid import ObjectId
from pymongo import ReadPreference, WriteConcern
from pymongo.read_preferences import Secondary
from pymongo.errors import DuplicateKeyError, OperationFailure
from tornado import gen
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import motor.motor_tornado
import test
from test import SkipTest
from test.tornado_tests import MotorTest, skip_if_mongos
from test.utils import ignore_deprecations


class MotorCollectionTest(MotorTest):
    @gen_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # MotorClient's accessors
        collection = motor.MotorCollection(self.db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        self.assertEqual('test_collection', collection.name)
        yield collection.insert_one({'_id': 1})
        doc = yield collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError,
            motor.MotorCollection,
            self.db,
            'test_collection',
            capped=True)

    @gen_test
    def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (
                self.db.foo.bar,
                self.db.foo.bar.baz):
            yield coll.delete_many({})
            result = yield coll.insert_one({'_id': 'xyzzy'})
            self.assertEqual('xyzzy', result.inserted_id)
            result = yield coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield coll.delete_many({})
            self.assertEqual(None, (yield coll.find_one({'_id': 'xyzzy'})))

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.db.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @ignore_deprecations
    @gen_test
    def test_update(self):
        yield self.collection.insert_one({'_id': 1})
        result = yield self.collection.update(
            {'_id': 1}, {'$set': {'foo': 'bar'}})

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result.get('err'))

    @ignore_deprecations
    @gen_test
    def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        coll = self.db.unique_collection
        yield coll.create_index('s', unique=True)

        try:
            yield coll.insert_many([{'s': 1}, {'s': 2}])
            with self.assertRaises(DuplicateKeyError):
                yield coll.update({'s': 2}, {'$set': {'s': 1}})

        finally:
            yield coll.drop()

    @gen_test
    def test_insert_one(self):
        collection = self.collection
        result = yield collection.insert_one({'_id': 201})
        self.assertEqual(201, result.inserted_id)

    @ignore_deprecations
    @gen_test
    def test_insert_many_one_bad(self):
        collection = self.collection
        yield collection.insert_one({'_id': 2})

        # Violate a unique index in one of many updates, handle error.
        with self.assertRaises(DuplicateKeyError):
            yield collection.insert([
                {'_id': 1},
                {'_id': 2},  # Already exists
                {'_id': 3}])

        # First insert should have succeeded, but not second or third.
        self.assertEqual(
            set([1, 2]),
            set((yield collection.distinct('_id'))))

    @ignore_deprecations
    @gen_test
    def test_save_callback(self):
        yield self.collection.save({}, callback=None)

        # Should not raise
        (result, error), _ = yield gen.Task(self.collection.save, {})
        if error:
            raise error

    @ignore_deprecations
    @gen_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5.
        self.assertEqual(
            5,
            (yield self.collection.save({'_id': 5})))

    @ignore_deprecations
    @gen_test
    def test_save_without_id(self):
        collection = self.collection
        result = yield collection.save({'fiddle': 'faddle'})

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))

    @ignore_deprecations
    @gen_test
    def test_save_bad(self):
        coll = self.db.unique_collection
        yield coll.ensure_index('s', unique=True)
        yield coll.save({'s': 1})

        try:
            with self.assertRaises(DuplicateKeyError):
                yield coll.save({'s': 1})
        finally:
            yield coll.drop()

    @gen_test
    def test_delete_one(self):
        # Remove a document twice, check that we get a success responses
        # and n = 0 for the second time.
        yield self.collection.insert_one({'_id': 1})
        result = yield self.collection.delete_one({'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result.raw_result['n'])
        self.assertEqual(1, result.raw_result['ok'])
        self.assertEqual(None, result.raw_result.get('err'))

        result = yield self.collection.delete_one({'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result.raw_result['n'])
        self.assertEqual(1, result.raw_result['ok'])
        self.assertEqual(None, result.raw_result.get('err'))

    @ignore_deprecations
    @gen_test
    def test_unacknowledged_insert(self):
        # Test that unsafe inserts with no callback still work

        # Insert id 1 without a callback or w=1.
        coll = self.db.test_unacknowledged_insert
        coll.with_options(write_concern=WriteConcern(0)).insert_one({'_id': 1})

        # The insert is eventually executed.
        while not (yield coll.count()):
            yield gen.sleep(0.1)

        # DuplicateKeyError not raised.
        future = coll.insert({'_id': 1})
        yield coll.insert({'_id': 1}, w=0)

        with self.assertRaises(DuplicateKeyError):
            yield future

    @ignore_deprecations
    @gen_test
    def test_unacknowledged_save(self):
        # Test that unsafe saves with no callback still work
        collection_name = 'test_unacknowledged_save'
        coll = self.db[collection_name]
        coll.save({'_id': 201}, w=0)

        while not (yield coll.find_one({'_id': 201})):
            yield gen.sleep(0.1)

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield coll.save({'_id': 201}, w=0)
        coll.database.client.close()

    @ignore_deprecations
    @gen_test
    def test_unacknowledged_update(self):
        # Test that unsafe updates with no callback still work
        coll = self.collection

        yield coll.insert_one({'_id': 1})
        coll.update({'_id': 1}, {'$set': {'a': 1}}, w=0)

        while not (yield coll.find_one({'a': 1})):
            yield gen.sleep(0.1)

        coll.database.client.close()

    @gen_test(timeout=30)
    def test_nested_callbacks(self):
        results = [0]
        future = Future()
        yield self.collection.delete_many({})
        yield self.collection.insert_one({'_id': 1})

        def callback(result, error):
            if error:
                future.set_exception(error)
            elif result:
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

    @ignore_deprecations
    @gen_test
    def test_indexes(self):
        test_collection = self.collection

        # Create an index
        idx_name = yield test_collection.create_index([('foo', 1)])
        index_info = yield test_collection.index_information()
        self.assertEqual([('foo', 1)], index_info[idx_name]['key'])

        # Ensure the same index, test that callback is executed
        result = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual('foo_1', result)
        result2 = yield test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result2)

        # Ensure an index that doesn't exist, test it's created
        yield test_collection.ensure_index([('bar', 1)])
        index_info = yield test_collection.index_information()
        self.assertTrue(any([
            info['key'] == [('bar', 1)] for info in index_info.values()]))

        # Don't test drop_index or drop_indexes -- Synchro tests them

    @gen.coroutine
    def _make_test_data(self, n):
        yield self.db.drop_collection("test")
        yield self.db.test.insert_many([{'_id': i} for i in range(n)])
        expected_sum = sum(range(n))
        raise gen.Return(expected_sum)

    pipeline = [{'$project': {'_id': '$_id'}}]

    def assertAllDocs(self, expected_sum, docs):
        self.assertEqual(expected_sum, sum(doc['_id'] for doc in docs))

    @gen_test(timeout=30)
    def test_aggregation_cursor(self):
        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            expected_sum = yield self._make_test_data(collection_size)
            cursor = db.test.aggregate(self.pipeline)
            docs = yield cursor.to_list(collection_size)
            self.assertAllDocs(expected_sum, docs)

    @gen_test
    def test_aggregation_cursor_exc_info(self):
        if sys.version_info < (3,):
            raise SkipTest("Requires Python 3")

        yield self._make_test_data(200)
        cursor = self.db.test.aggregate(self.pipeline)
        yield cursor.to_list(length=10)
        yield self.db.test.drop()
        try:
            yield cursor.to_list(length=None)
        except OperationFailure:
            _, _, tb = sys.exc_info()

            # The call tree should include PyMongo code we ran on a thread.
            formatted = '\n'.join(traceback.format_tb(tb))
            self.assertTrue('_unpack_response' in formatted
                            or '_check_command_response' in formatted)

    @gen_test(timeout=30)
    def test_aggregation_cursor_to_list_callback(self):
        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            expected_sum = yield self._make_test_data(collection_size)
            cursor = db.test.aggregate(self.pipeline)
            future = Future()

            def cb(result, error):
                if error:
                    future.set_exception(error)
                else:
                    future.set_result(result)

            cursor.to_list(collection_size, callback=cb)
            docs = yield future
            self.assertAllDocs(expected_sum, docs)

    @gen_test(timeout=30)
    def test_parallel_scan(self):
        yield skip_if_mongos(self.cx)

        collection = self.collection.with_options(
            write_concern=WriteConcern(test.env.w))

        # Enough documents that each cursor requires multiple batches.
        yield collection.delete_many({})
        yield collection.insert_many(({'_id': i} for i in range(8000)))
        if test.env.is_replica_set:
            # Test that getMore messages are sent to the right server.
            client = self.motor_rsc(read_preference=Secondary())
            collection = client.motor_test.test_collection

        docs = []

        @gen.coroutine
        def f(cursor):
            self.assertTrue(isinstance(cursor,
                                       motor.motor_tornado.MotorCommandCursor))

            while (yield cursor.fetch_next):
                docs.append(cursor.next_object())

        cursors = yield collection.parallel_scan(3)
        yield [f(cursor) for cursor in cursors]
        self.assertEqual(len(docs), (yield collection.count()))

    def test_with_options(self):
        coll = self.db.test
        codec_options = CodecOptions(
            tz_aware=True, uuid_representation=JAVA_LEGACY)

        write_concern = WriteConcern(w=2, j=True)
        coll2 = coll.with_options(
            codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(coll2, motor.MotorCollection))
        self.assertEqual(codec_options, coll2.codec_options)
        self.assertEqual(Secondary(), coll2.read_preference)
        self.assertEqual(write_concern, coll2.write_concern)

        pref = Secondary([{"dc": "sf"}])
        coll2 = coll.with_options(read_preference=pref)
        self.assertEqual(pref, coll2.read_preference)
        self.assertEqual(coll.codec_options, coll2.codec_options)
        self.assertEqual(coll.write_concern, coll2.write_concern)


if __name__ == '__main__':
    unittest.main()
