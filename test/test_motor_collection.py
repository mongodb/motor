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
import pymongo
from tornado import gen, ioloop
from bson.objectid import ObjectId
from pymongo.errors import DuplicateKeyError
from test.utils import delay

import motor
from test import host, port
from test import MotorTest, async_test_engine, AssertEqual, AssertRaises


class MotorCollectionTest(MotorTest):
    @async_test_engine()
    def test_collection(self, done):
        # Test that we can create a collection directly, not just from
        # MotorClient's accessors
        db = self.motor_client(host, port).pymongo_test
        collection = motor.MotorCollection(db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        doc = yield motor.Op(collection.find_one, {'_id': 1})
        self.assertEqual(1, doc['_id'])
        done()

    @async_test_engine()
    def test_dotted_collection_name(self, done):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        cx = self.motor_client(host, port)
        for coll in (
            cx.pymongo_test.foo,
            cx.pymongo_test.foo.bar,
            cx.pymongo_test.foo.bar.baz.quux
        ):
            yield motor.Op(coll.remove)
            yield AssertEqual('xyzzy', coll.insert, {'_id':'xyzzy'})
            result = yield motor.Op(coll.find_one, {'_id':'xyzzy'})
            self.assertEqual(result['_id'], 'xyzzy')
            yield motor.Op(coll.remove)
            yield AssertEqual(None, coll.find_one, {'_id':'xyzzy'})

        done()

    @async_test_engine()
    def test_find_where(self, done):
        # Check that $where clauses work
        coll = self.motor_client(host, port).pymongo_test.test_collection
        res = yield motor.Op(coll.find().to_list, length=1000)
        self.assertEqual(200, len(res))

        # Get the one doc with _id of 8
        where = 'this._id == 2 * 4'
        res0 = yield motor.Op(coll.find({'$where': where}).to_list, length=1000)
        self.assertEqual(1, len(res0))
        self.assertEqual(8, res0[0]['_id'])

        res1 = yield motor.Op(coll.find().where(where).to_list, length=1000)
        self.assertEqual(res0, res1)
        done()

    @async_test_engine()
    def test_find_callback(self, done):
        cx = self.motor_client(host, port)
        cursor = cx.pymongo_test.test_collection.find()
        yield motor.Op(self.check_required_callback, cursor.each)

        # Avoid triggering length warning here, test_to_list_length_warning
        # must be the only place it's raised
        yield motor.Op(self.check_required_callback, cursor.to_list, length=1)
        done()

    @async_test_engine()
    def test_find_is_async(self, done):
        # Confirm find() is async by launching two operations which will finish
        # out of order. Also test that MotorClient doesn't reuse sockets
        # incorrectly.
        cx = self.motor_client(host, port)

        # Launch find operations for _id's 1 and 2 which will finish in order
        # 2, then 1.
        results = []

        yield_points = [(yield gen.Callback(0)), (yield gen.Callback(1))]

        def callback(result, error):
            if result:
                results.append(result)
                yield_points.pop()()

        # This find() takes 0.5 seconds
        cx.pymongo_test.test_collection.find(
            {'_id': 1, '$where': delay(0.5)},
            fields={'s': True, '_id': False}
        ).limit(1).each(callback)

        # Very fast lookup
        cx.pymongo_test.test_collection.find(
            {'_id': 2},
            fields={'s': True, '_id': False}
        ).limit(1).each(callback)

        yield gen.WaitAll([0, 1])

        # Results were appended in order 2, 1
        self.assertEqual(
            [{'s': hex(s)} for s in (2, 1)],
            results)

        done()

    @async_test_engine()
    def test_find_and_cancel(self, done):
        cx = self.motor_client(host, port)
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

        cursor = cx.pymongo_test.test_collection.find(sort=[('s', 1)])
        cursor.each(callback)
        yield gen.Wait(0)

        # There are 200 docs, but we canceled after 2
        self.assertEqual(
            [
                {'_id': 0, 's': hex(0)},
                {'_id': 1, 's': hex(1)},
            ],
            results)

        yield motor.Op(cursor.close)
        done()

    @async_test_engine()
    def test_find_one(self, done):
        cx = self.motor_client(host, port)
        yield AssertEqual(
            {'_id': 1, 's': hex(1)},
            cx.pymongo_test.test_collection.find_one,
            {'_id': 1})
        done()

    @async_test_engine()
    def test_find_one_callback(self, done):
        cx = self.motor_client(host, port)
        yield motor.Op(
            self.check_required_callback,
            cx.pymongo_test.test_collection.find_one)

        done()

    @async_test_engine(timeout_sec=6)
    def test_find_one_is_async(self, done):
        # Confirm find_one() is async by launching two operations which will
        # finish out of order.
        cx = self.motor_client(host, port)

        def callback(result, error):
            if error:
                raise error
            results.append(result)

        # Launch 2 find_one operations for _id's 1 and 2, which will finish in
        # order 2 then 1.
        results = []

        yield_points = [(yield gen.Callback(0)), (yield gen.Callback(1))]

        def callback(result, error):
            if result:
                results.append(result)
                yield_points.pop()()

        # This find_one() takes 5 seconds
        cx.pymongo_test.test_collection.find_one(
            {'_id': 1, '$where': delay(5)},
            fields={'s': True, '_id': False},
            callback=callback)

        # Very fast lookup
        cx.pymongo_test.test_collection.find_one(
            {'_id': 2},
            fields={'s': True, '_id': False},
            callback=callback)

        yield gen.WaitAll([0, 1])

        # Results were appended in order 2, 1
        self.assertEqual(
            [{'s': hex(s)} for s in (2, 1)],
            results)

        done()

    @async_test_engine()
    def test_update(self, done):
        cx = self.motor_client(host, port)
        result = yield motor.Op(cx.pymongo_test.test_collection.update,
            {'_id': 5},
            {'$set': {'foo': 'bar'}},
        )

        self.assertEqual(1, result['ok'])
        self.assertEqual(True, result['updatedExisting'])
        self.assertEqual(1, result['n'])
        self.assertEqual(None, result['err'])
        done()

    @async_test_engine()
    def test_update_bad(self, done):
        # Violate a unique index, make sure we handle error well
        cx = self.motor_client(host, port)

        # There's already a document with s: hex(4)
        yield AssertRaises(DuplicateKeyError,
            cx.pymongo_test.test_collection.update,
            {'_id': 5},
            {'$set': {'s': hex(4)}})

        done()

    @async_test_engine()
    def test_update_callback(self, done):
        cx = self.motor_client(host, port)
        yield motor.Op(
            self.check_optional_callback,
            cx.pymongo_test.test_collection.update, {}, {})

        done()

    @async_test_engine()
    def test_insert(self, done):
        cx = self.motor_client(host, port)
        yield AssertEqual(
            201,
            cx.pymongo_test.test_collection.insert,
            {'_id': 201}
        )
        done()

    @async_test_engine()
    def test_insert_many(self, done):
        cx = self.motor_client(host, port)
        yield AssertEqual(
            range(201, 211),
            cx.pymongo_test.test_collection.insert,
            [{'_id': i, 's': hex(i)} for i in range(201, 211)]
        )
        done()

    @async_test_engine()
    def test_insert_bad(self, done):
        # Violate a unique index, make sure we handle error well
        cx = self.motor_client(host, port)
        yield AssertRaises(
            DuplicateKeyError,
            cx.pymongo_test.test_collection.insert,
            {'s': hex(4)} # There's already a document with s: hex(4)
        )
        done()

    def test_insert_many_one_bad(self):
        # Violate a unique index in one of many updates, handle error
        cx = self.motor_client(host, port)
        result = yield AssertRaises(
            DuplicateKeyError,
            cx.pymongo_test.test_collection.insert,
            [
                {'_id': 201, 's': hex(201)},
                {'_id': 202, 's': hex(4)}, # Already exists
                {'_id': 203, 's': hex(203)},
            ]
        )

        # Even though first insert succeeded, an exception was raised and
        # result is None
        self.assertEqual(None, result)

        # First insert should've succeeded
        yield AssertEqual(
            [{'_id': 201, 's': hex(201)}],
            self.sync_db.test_collection.find({'_id': 201}).to_list,
            length=1000)

        # Final insert didn't execute, since second failed
        yield AssertEqual(
            [],
            self.sync_db.test_collection.find({'_id': 203}).to_list,
            length=1000)

    @async_test_engine()
    def test_save_callback(self, done):
        cx = self.motor_client(host, port)
        yield motor.Op(
            self.check_optional_callback,
            cx.pymongo_test.test_collection.save, {})

        done()

    @async_test_engine()
    def test_save_with_id(self, done):
        # save() returns the _id, in this case 5
        yield AssertEqual(
            5,
            self.motor_client(host, port).pymongo_test.test_collection.save,
            {'_id': 5}
        )
        done()

    @async_test_engine()
    def test_save_without_id(self, done):
        result = yield motor.Op(
            self.motor_client(host, port).pymongo_test.test_collection.save,
            {'fiddle': 'faddle'}
        )

        # save() returns the new _id
        self.assertTrue(isinstance(result, ObjectId))
        done()

    @async_test_engine()
    def test_save_bad(self, done):
        # Violate a unique index, make sure we handle error well
        yield AssertRaises(
            DuplicateKeyError,
            self.motor_client(host, port).pymongo_test.test_collection.save,
            {'_id': 5, 's': hex(4)} # There's already a document with s: hex(4)
        )
        done()

    @async_test_engine()
    def test_remove(self, done):
        # Remove a document twice, check that we get a success response first
        # time and an error the second time.
        cx = self.motor_client(host, port)
        result = yield motor.Op(
            cx.pymongo_test.test_collection.remove, {'_id': 1})

        # First time we remove, n = 1
        self.assertEqual(1, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result['err'])

        result = yield motor.Op(
            cx.pymongo_test.test_collection.remove, {'_id': 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result['n'])
        self.assertEqual(1, result['ok'])
        self.assertEqual(None, result['err'])
        done()

    @async_test_engine()
    def test_remove_callback(self, done):
        cx = self.motor_client(host, port)
        yield motor.Op(
            self.check_optional_callback,
            cx.pymongo_test.test_collection.remove)

        done()

    @async_test_engine()
    def test_unacknowledged_remove(self, done):
        # Test that unsafe removes with no callback still work
        def ndocs():
            return self.sync_coll.find(
                {'_id': {'$gte': 115, '$lte': 117}}).count()

        self.assertEqual(3, ndocs(), msg="Test setup should have 3 documents")
        coll = self.motor_client(host, port).pymongo_test.test_collection
        # Unacknowledged removes
        coll.remove({'_id': 115})
        coll.remove({'_id': 116})
        coll.remove({'_id': 117})
        # Wait for them to complete
        loop = ioloop.IOLoop.instance()
        while ndocs():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        done()

    @async_test_engine()
    def test_unacknowledged_insert(self, done):
        # Test that unsafe inserts with no callback still work

        # id 201 not present
        self.assertEqual(0, self.sync_coll.find({'_id': 201}).count())

        # insert id 201 without a callback or w=1
        coll = self.motor_client(host, port).pymongo_test.test_collection
        coll.insert({'_id': 201})

        # the insert is eventually executed
        loop = ioloop.IOLoop.instance()
        while not self.sync_db.test_collection.find({'_id': 201}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        # DuplicateKeyError not raised
        coll.insert({'_id': 201})
        yield motor.Op(coll.insert, {'_id': 201}, w=0)
        done()

    @async_test_engine()
    def test_unacknowledged_save(self, done):
        # Test that unsafe saves with no callback still work
        coll = self.motor_client(host, port).pymongo_test.test_collection
        coll.save({'_id': 201})

        loop = ioloop.IOLoop.instance()
        while not self.sync_db.test_collection.find({'_id': 201}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        # DuplicateKeyError not raised
        coll.save({'_id': 201})
        yield motor.Op(coll.save, {'_id': 201}, w=0)
        done()

    @async_test_engine()
    def test_unacknowledged_update(self, done):
        # Test that unsafe updates with no callback still work
        coll = self.motor_client(host, port).pymongo_test.test_collection
        coll.update({'_id': 100}, {'$set': {'a': 1}})

        loop = ioloop.IOLoop.instance()
        while not self.sync_db.test_collection.find({'a': 1}).count():
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        done()

    @async_test_engine()
    def test_nested_callbacks(self, done):
        cx = self.motor_client(host, port)
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
                cx.pymongo_test.test_collection.find(
                    {'_id': 1},
                    {'s': False},
                ).each(callback)
            else:
                yield_point()

        cx.pymongo_test.test_collection.find(
            {'_id': 1},
            {'s': False},
        ).each(callback)

        yield gen.Wait(0)

        self.assertEqual(
            1000,
            results[0])
        done()

    @async_test_engine()
    def test_nested_callbacks_2(self, done):
        cx = motor.MotorClient(host, port)
        yield_point = yield gen.Callback(0)

        def connected(cx, error):
            if error:
                raise error

            cx.pymongo_test.test_collection.insert({'_id': 201},
                callback=inserted)

        def inserted(result, error):
            if error:
                raise error

            cx.pymongo_test.test_collection.find_one({'_id': 201},
                callback=found)

        def found(result, error):
            if error:
                raise error

            cx.pymongo_test.test_collection.remove({'_id': 201},
                callback=removed)

        def removed(result, error):
            yield_point()

        cx.open(connected)
        yield gen.Wait(0)
        done()

    @async_test_engine()
    def test_map_reduce(self, done):
        # Count number of documents with even and odd _id
        expected_result = [{'_id': 0, 'value': 100}, {'_id': 1, 'value': 100}]
        map = bson.Code('function map() { emit(this._id % 2, 1); }')
        reduce = bson.Code('''
        function reduce(key, values) {
            r = 0;
            values.forEach(function(value) { r += value; });
            return r;
        }''')

        cx = self.motor_client(host, port)
        yield motor.Op(cx.pymongo_test.tmp_mr.drop)

        # First do a standard mapreduce, should return MotorCollection
        tmp_mr = yield motor.Op(cx.pymongo_test.test_collection.map_reduce,
            map, reduce, 'tmp_mr')

        self.assertTrue(isinstance(tmp_mr, motor.MotorCollection),
            'map_reduce should return MotorCollection, not %s' % tmp_mr)

        result = yield motor.Op(
            tmp_mr.find().sort([('_id', 1)]).to_list, length=1000)
        self.assertEqual(expected_result, result)

        # Standard mapreduce with full response
        yield motor.Op(cx.pymongo_test.tmp_mr.drop)
        response = yield motor.Op(cx.pymongo_test.test_collection.map_reduce,
            map, reduce, 'tmp_mr', full_response=True)

        self.assertTrue(
            isinstance(response, dict),
            'map_reduce should return dict, not %s' % response)

        self.assertEqual('tmp_mr', response['result'])
        result = yield motor.Op(
            tmp_mr.find().sort([('_id', 1)]).to_list, length=1000)
        self.assertEqual(expected_result, result)

        # Inline mapreduce
        yield motor.Op(cx.pymongo_test.tmp_mr.drop)
        result = yield motor.Op(
            cx.pymongo_test.test_collection.inline_map_reduce, map, reduce)

        result.sort(key=lambda doc: doc['_id'])
        self.assertEqual(expected_result, result)
        done()

    @async_test_engine()
    def test_indexes(self, done):
        cx = self.motor_client(host, port)
        test_collection = cx.pymongo_test.test_collection

        # Create an index
        idx_name = yield motor.Op(test_collection.create_index, [('foo', 1)])
        index_info = yield motor.Op(test_collection.index_information)
        self.assertEqual([('foo', 1)], index_info[idx_name]['key'])

        # Ensure the same index, test that callback is executed
        result = yield motor.Op(test_collection.ensure_index, [('foo', 1)])
        self.assertEqual(None, result)
        result2 = yield motor.Op(test_collection.ensure_index, [('foo', 1)])
        self.assertEqual(None, result2)

        # Ensure an index that doesn't exist, test it's created
        yield motor.Op(test_collection.ensure_index, [('bar', 1)])
        index_info = yield motor.Op(test_collection.index_information)
        self.assertTrue(any([
            info['key'] == [('bar', 1)] for info in index_info.values()
        ]))
        done()

        # Don't test drop_index or drop_indexes -- Synchro tests them
        

if __name__ == '__main__':
    unittest.main()
