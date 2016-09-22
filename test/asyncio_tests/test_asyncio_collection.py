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

"""Test AsyncIOMotorCollection."""

import asyncio
import unittest
from unittest import SkipTest

import bson
from bson import CodecOptions
from bson.binary import JAVA_LEGACY, OLD_UUID_SUBTYPE
from bson.objectid import ObjectId
from pymongo import ReadPreference, WriteConcern
from pymongo.errors import DuplicateKeyError
from pymongo.read_preferences import Secondary

from motor import motor_asyncio
from motor.motor_asyncio import AsyncIOMotorCollection, \
    AsyncIOMotorCommandCursor
import test
from test.asyncio_tests import (asyncio_test, AsyncIOTestCase,
                                skip_if_mongos, at_least)
from test.utils import delay, ignore_deprecations


class TestAsyncIOCollection(AsyncIOTestCase):
    @asyncio_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # database accessors.
        collection = AsyncIOMotorCollection(self.db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        self.assertEqual('test_collection', collection.name)
        yield from collection.remove()
        yield from collection.insert({'_id': 1})
        doc = yield from collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError,
            AsyncIOMotorCollection,
            self.db,
            'test_collection',
            capped=True)

    @asyncio_test
    def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (
                self.db.foo.bar,
                self.db.foo.bar.baz):
            yield from coll.remove()
            self.assertEqual('xyzzy',
                             (yield from coll.insert({'_id': 'xyzzy'})))
            result = yield from coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield from coll.remove()
            resp = yield from coll.find_one({'_id': 'xyzzy'})
            self.assertEqual(None, resp)

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.db.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @asyncio_test(timeout=30)
    def test_find_is_async(self):
        # Confirm find() is async by launching two operations which will finish
        # out of order. Also test that AsyncIOMotorClient doesn't reuse sockets
        # incorrectly.

        # Launch find operations for _id's 1 and 2 which will finish in order
        # 2, then 1.
        coll = self.collection
        yield from coll.insert([{'_id': 1}, {'_id': 2}])
        results = []

        futures = [asyncio.Future(loop=self.loop),
                   asyncio.Future(loop=self.loop)]

        def callback(result, error):
            if result:
                results.append(result)
                futures.pop().set_result(None)

        # This find() takes 0.5 seconds.
        coll.find({'_id': 1, '$where': delay(0.5)}).limit(1).each(callback)

        # Very fast lookup.
        coll.find({'_id': 2}).limit(1).each(callback)

        yield from asyncio.gather(*futures, loop=self.loop)

        # Results were appended in order 2, 1.
        self.assertEqual([{'_id': 2}, {'_id': 1}], results)

    @asyncio_test
    def test_update(self):
        yield from self.collection.insert({'_id': 1})
        result = yield from self.collection.update(
            {'_id': 1}, {'$set': {'foo': 'bar'}})

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result.get('err'))

    @asyncio_test
    def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        coll = self.db.unique_collection
        yield from coll.ensure_index('s', unique=True)

        try:
            yield from coll.insert([{'s': 1}, {'s': 2}])
            with self.assertRaises(DuplicateKeyError):
                yield from coll.update({'s': 2}, {'$set': {'s': 1}})

        finally:
            yield from coll.drop()

    @asyncio_test
    def test_insert(self):
        collection = self.collection
        self.assertEqual(201, (yield from collection.insert({'_id': 201})))

    @asyncio_test
    def test_insert_many_one_bad(self):
        collection = self.collection
        yield from collection.insert({'_id': 2})

        # Violate a unique index in one of many updates, handle error.
        with self.assertRaises(DuplicateKeyError):
            yield from collection.insert([
                {'_id': 1},
                {'_id': 2},  # Already exists
                {'_id': 3}])

        # First insert should have succeeded, but not second or third.
        self.assertEqual(
            set([1, 2]),
            set((yield from collection.distinct('_id'))))

    @asyncio_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5.
        self.assertEqual(
            5,
            (yield from self.collection.save({'_id': 5})))

    @asyncio_test
    def test_save_without_id(self):
        collection = self.collection
        result = yield from collection.save({'fiddle': 'faddle'})

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))

    @asyncio_test
    def test_save_bad(self):
        coll = self.db.unique_collection
        yield from coll.ensure_index('s', unique=True)
        yield from coll.save({'s': 1})

        try:
            with self.assertRaises(DuplicateKeyError):
                yield from coll.save({'s': 1})
        finally:
            yield from coll.drop()

    @asyncio_test
    def test_remove(self):
        # Remove a document twice, check that we get a success responses
        # and n = 0 for the second time.
        yield from self.collection.insert({'_id': 1})
        result = yield from self.collection.remove({'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

        result = yield from self.collection.remove({'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result.get('err'))

    @asyncio_test
    def test_unacknowledged_remove(self):
        coll = self.collection
        yield from coll.remove()
        yield from coll.insert([{'_id': i} for i in range(3)])

        # Don't yield from the futures.
        coll.remove({'_id': 0}, w=0)
        coll.remove({'_id': 1}, w=0)
        coll.remove({'_id': 2}, w=0)

        # Wait for them to complete
        while (yield from coll.count()):
            yield from asyncio.sleep(0.1, loop=self.loop)

        coll.database.client.close()

    @asyncio_test
    def test_unacknowledged_insert(self):
        coll = self.db.test_unacknowledged_insert
        coll.insert({'_id': 1}, w=0)

        # The insert is eventually executed.
        while not (yield from coll.count()):
            yield from asyncio.sleep(0.1, loop=self.loop)

        # DuplicateKeyError not raised.
        future = coll.insert({'_id': 1})
        yield from coll.insert({'_id': 1}, w=0)

        with self.assertRaises(DuplicateKeyError):
            yield from future

    @asyncio_test
    def test_unacknowledged_save(self):
        # Test that unsafe saves with no callback still work
        collection_name = 'test_unacknowledged_save'
        coll = self.db[collection_name]
        future = coll.save({'_id': 201}, w=0)

        while not (yield from coll.find_one({'_id': 201})):
            yield from asyncio.sleep(0.1, loop=self.loop)

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield from coll.save({'_id': 201}, w=0)

        # Clean up.
        yield from future
        coll.database.client.close()

    @asyncio_test
    def test_unacknowledged_update(self):
        # Test that unsafe updates with no callback still work
        coll = self.collection

        yield from coll.insert({'_id': 1})
        coll.update({'_id': 1}, {'$set': {'a': 1}}, w=0)

        while not (yield from coll.find_one({'a': 1})):
            yield from asyncio.sleep(0.1, loop=self.loop)

        coll.database.client.close()

    @asyncio_test
    def test_nested_callbacks(self):
        results = [0]
        future = asyncio.Future(loop=self.loop)
        yield from self.collection.remove()
        yield from self.collection.insert({'_id': 1})

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

        yield from future
        self.assertEqual(1000, results[0])

    @asyncio_test
    def test_map_reduce(self):
        # Count number of documents with even and odd _id
        yield from self.make_test_data()
        expected_result = [{'_id': 0, 'value': 100}, {'_id': 1, 'value': 100}]
        map_fn = bson.Code('function map() { emit(this._id % 2, 1); }')
        reduce_fn = bson.Code('''
        function reduce(key, values) {
            r = 0;
            values.forEach(function(value) { r += value; });
            return r;
        }''')

        yield from self.db.tmp_mr.drop()

        # First do a standard mapreduce, should return AsyncIOMotorCollection
        collection = self.collection
        tmp_mr = yield from collection.map_reduce(map_fn, reduce_fn, 'tmp_mr')

        self.assertTrue(
            isinstance(tmp_mr, motor_asyncio.AsyncIOMotorCollection),
            'map_reduce should return AsyncIOMotorCollection, not %s' % tmp_mr)

        result = yield from tmp_mr.find().sort([('_id', 1)]).to_list(
            length=1000)
        self.assertEqual(expected_result, result)

        # Standard mapreduce with full response
        yield from self.db.tmp_mr.drop()
        response = yield from collection.map_reduce(
            map_fn, reduce_fn, 'tmp_mr', full_response=True)

        self.assertTrue(
            isinstance(response, dict),
            'map_reduce should return dict, not %s' % response)

        self.assertEqual('tmp_mr', response['result'])
        result = yield from tmp_mr.find().sort([('_id', 1)]).to_list(
            length=1000)
        self.assertEqual(expected_result, result)

        # Inline mapreduce
        yield from self.db.tmp_mr.drop()
        result = yield from collection.inline_map_reduce(
            map_fn, reduce_fn)

        result.sort(key=lambda doc: doc['_id'])
        self.assertEqual(expected_result, result)

    @asyncio_test
    def test_indexes(self):
        test_collection = self.collection

        # Create an index
        idx_name = yield from test_collection.create_index([('foo', 1)])
        index_info = yield from test_collection.index_information()
        self.assertEqual([('foo', 1)], index_info[idx_name]['key'])

        # Ensure the same index, test that callback is executed
        result = yield from test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result)
        result2 = yield from test_collection.ensure_index([('foo', 1)])
        self.assertEqual(None, result2)

        # Ensure an index that doesn't exist, test it's created
        yield from test_collection.ensure_index([('bar', 1)])
        index_info = yield from test_collection.index_information()
        self.assertTrue(any([
            info['key'] == [('bar', 1)] for info in index_info.values()]))

        # Don't test drop_index or drop_indexes -- Synchro tests them

    @asyncio_test
    def test_aggregation_cursor(self):
        mongo_2_5_1 = yield from at_least(self.cx, (2, 5, 1))

        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            yield from db.drop_collection("test")
            yield from db.test.insert([{'_id': i} for i in
                                       range(collection_size)])
            pipeline = {'$project': {'_id': '$_id'}}
            expected_sum = sum(range(collection_size))

            reply = yield from db.test.aggregate(pipeline, cursor=False)
            self.assertEqual(expected_sum,
                             sum(doc['_id'] for doc in reply['result']))

            if mongo_2_5_1:
                cursor = db.test.aggregate(pipeline)
                docs = yield from cursor.to_list(collection_size)
                self.assertEqual(expected_sum,
                                 sum(doc['_id'] for doc in docs))

    @asyncio_test(timeout=30)
    def test_parallel_scan(self):
        if not (yield from at_least(self.cx, (2, 5, 5))):
            raise SkipTest("Requires MongoDB >= 2.5.5")

        yield from skip_if_mongos(self.cx)

        collection = self.collection

        # Enough documents that each cursor requires multiple batches.
        yield from collection.remove()
        yield from collection.insert(({'_id': i} for i in range(8000)),
                                     w=test.env.w)
        if test.env.is_replica_set:
            client = self.asyncio_rsc()

            # Test that getMore messages are sent to the right server.
            client.read_preference = ReadPreference.SECONDARY
            collection = client.motor_test.test_collection

        docs = []

        @asyncio.coroutine
        def f(cursor):
            self.assertTrue(isinstance(cursor, AsyncIOMotorCommandCursor))

            while (yield from cursor.fetch_next):
                docs.append(cursor.next_object())

        cursors = yield from collection.parallel_scan(3)
        yield from asyncio.wait(
            [f(cursor) for cursor in cursors],
            loop=self.loop)

        self.assertEqual(len(docs), (yield from collection.count()))

    def test_uuid_subtype(self):
        collection = self.db.test

        with ignore_deprecations():
            self.assertEqual(collection.uuid_subtype, OLD_UUID_SUBTYPE)
            collection.uuid_subtype = JAVA_LEGACY
            self.assertEqual(collection.uuid_subtype, JAVA_LEGACY)

    def test_with_options(self):
        coll = self.db.test
        codec_options = CodecOptions(
            tz_aware=True, uuid_representation=JAVA_LEGACY)

        write_concern = WriteConcern(w=2, j=True)
        coll2 = coll.with_options(
            codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(coll2, AsyncIOMotorCollection))
        self.assertEqual(codec_options, coll2.codec_options)
        self.assertEqual(JAVA_LEGACY, coll2.uuid_subtype)
        self.assertEqual(ReadPreference.SECONDARY, coll2.read_preference)
        self.assertEqual(write_concern.document, coll2.write_concern)

        pref = Secondary([{"dc": "sf"}])
        coll2 = coll.with_options(read_preference=pref)
        self.assertEqual(pref.mode, coll2.read_preference)
        self.assertEqual(pref.tag_sets, coll2.tag_sets)
        self.assertEqual(coll.codec_options, coll2.codec_options)
        self.assertEqual(coll.uuid_subtype, coll2.uuid_subtype)
        self.assertEqual(coll.write_concern, coll2.write_concern)


if __name__ == '__main__':
    unittest.main()
