# Copyright 2013 10gen, Inc.
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

import pymongo
from pymongo.errors import InvalidOperation

import motor
from test import host, port
from test import MotorTest, async_test_engine, AssertRaises


class MotorTestBasic(MotorTest):
    def test_repr(self):
        cx = self.motor_client(host, port)
        self.assertTrue(repr(cx).startswith('MotorClient'))
        db = cx.pymongo_test
        self.assertTrue(repr(db).startswith('MotorDatabase'))
        coll = db.test_collection
        self.assertTrue(repr(coll).startswith('MotorCollection'))
        cursor = coll.find()
        self.assertTrue(repr(cursor).startswith('MotorCursor'))

    @async_test_engine()
    def test_write_concern(self, done):
        cx = motor.MotorClient(host, port)

        # An implementation quirk of Motor, can't access properties until
        # connected
        self.assertRaises(
            pymongo.errors.InvalidOperation, getattr, cx, 'write_concern')

        yield motor.Op(cx.open)

        # Default empty dict means "w=1"
        self.assertEqual({}, cx.write_concern)

        for gle_options in [
            {},
            {'w': 0},
            {'w': 1},
            {'wtimeout': 1000},
            {'j': True},
        ]:
            cx = motor.MotorClient(host, port, **gle_options)
            yield motor.Op(cx.open)
            expected_wc = gle_options.copy()
            self.assertEqual(expected_wc, cx.write_concern)

            db = cx.pymongo_test
            self.assertEqual(expected_wc, db.write_concern)

            collection = db.test_collection
            self.assertEqual(expected_wc, collection.write_concern)

            # Call GLE whenever passing a callback, even if
            # collection.write_concern['w'] == 0
            yield AssertRaises(pymongo.errors.DuplicateKeyError,
                collection.insert, {'_id': 0})

            # No error
            yield motor.Op(collection.insert, {'_id': 0}, w=0)

            # Motor doesn't support 'safe'
            self.assertRaises(AssertionError, collection.insert, {}, safe=False)
            self.assertRaises(AssertionError, collection.insert, {}, safe=True)

        collection = cx.pymongo_test.test_collection
        collection.write_concern['w'] = 2

        # No error
        yield motor.Op(collection.insert, {'_id': 0}, w=0)

        cxw2 = yield motor.Op(motor.MotorClient(host, port, w=2).open)
        yield motor.Op(
            cxw2.pymongo_test.test_collection.insert, {'_id': 0}, w=0)

        # Test write concerns passed to MotorClient, set on collection, or
        # passed to insert.
        if self.is_replica_set:
            yield AssertRaises(pymongo.errors.DuplicateKeyError,
                cxw2.pymongo_test.test_collection.insert, {'_id': 0})

            yield AssertRaises(pymongo.errors.DuplicateKeyError,
                collection.insert, {'_id': 0})

            yield AssertRaises(pymongo.errors.DuplicateKeyError,
                cx.pymongo_test.test_collection.insert, {'_id': 0}, w=2)
        else:
            # w > 1 and no replica set
            yield AssertRaises(pymongo.errors.OperationFailure,
                cxw2.pymongo_test.test_collection.insert, {'_id': 0})

            yield AssertRaises(pymongo.errors.OperationFailure,
                collection.insert, {'_id': 0})

            yield AssertRaises(pymongo.errors.OperationFailure,
                cx.pymongo_test.test_collection.insert, {'_id': 0}, w=2)

        # Important that the last operation on each MotorClient was
        # acknowledged, so lingering messages aren't delivered in the middle of
        # the next test
        done()
