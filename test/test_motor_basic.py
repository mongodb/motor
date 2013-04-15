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
from pymongo.errors import ConfigurationError
from pymongo.read_preferences import ReadPreference

import motor
from test import host, port
from test import MotorTest, async_test_engine


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
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield motor.Op(collection.insert, {'_id': 0})

            # No error
            yield motor.Op(collection.insert, {'_id': 0}, w=0)

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
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield motor.Op(
                    cxw2.pymongo_test.test_collection.insert, {'_id': 0})

            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield motor.Op(collection.insert, {'_id': 0})

            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield motor.Op(
                    cx.pymongo_test.test_collection.insert, {'_id': 0}, w=2)
        else:
            # w > 1 and no replica set
            with self.assertRaises(pymongo.errors.OperationFailure):
                yield motor.Op(
                    cxw2.pymongo_test.test_collection.insert, {'_id': 0})

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield motor.Op(collection.insert, {'_id': 0})

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield motor.Op(
                    cx.pymongo_test.test_collection.insert, {'_id': 0}, w=2)

        # Important that the last operation on each MotorClient was
        # acknowledged, so lingering messages aren't delivered in the middle of
        # the next test
        done()

    @async_test_engine()
    def test_read_preference(self, done):
        cx = motor.MotorClient(host, port)

        # An implementation quirk of Motor, can't access properties until
        # connected
        self.assertRaises(
            pymongo.errors.InvalidOperation, getattr, cx, 'read_preference')

        # Check the default
        yield motor.Op(cx.open)
        self.assertEqual(ReadPreference.PRIMARY, cx.read_preference)

        # We can set mode, tags, and latency, both with open() and open_sync()
        cx = yield motor.Op(motor.MotorClient(
            host, port, read_preference=ReadPreference.SECONDARY,
            tag_sets=[{'foo': 'bar'}],
            secondary_acceptable_latency_ms=42).open)

        self.assertEqual(ReadPreference.SECONDARY, cx.read_preference)
        self.assertEqual([{'foo': 'bar'}], cx.tag_sets)
        self.assertEqual(42, cx.secondary_acceptable_latency_ms)

        cx = motor.MotorClient(
            host, port, read_preference=ReadPreference.SECONDARY,
            tag_sets=[{'foo': 'bar'}],
            secondary_acceptable_latency_ms=42).open_sync()

        self.assertEqual(ReadPreference.SECONDARY, cx.read_preference)
        self.assertEqual([{'foo': 'bar'}], cx.tag_sets)
        self.assertEqual(42, cx.secondary_acceptable_latency_ms)

        # Make a MotorCursor and get its PyMongo Cursor
        cursor = cx.pymongo_test.test_collection.find(
            read_preference=ReadPreference.NEAREST,
            tag_sets=[{'yay': 'jesse'}],
            secondary_acceptable_latency_ms=17).delegate

        self.assertEqual(
            ReadPreference.NEAREST, cursor._Cursor__read_preference)

        self.assertEqual([{'yay': 'jesse'}], cursor._Cursor__tag_sets)
        self.assertEqual(17, cursor._Cursor__secondary_acceptable_latency_ms)
        done()

    @async_test_engine()
    def test_safe(self, done):
        # Motor doesn't support 'safe'
        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, safe=True)

        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, safe=False)

        cx = motor.MotorClient(host, port)
        yield motor.Op(cx.open)
        collection = cx.pymongo_test.test_collection

        self.assertRaises(
            ConfigurationError, collection.insert, {}, safe=False)

        self.assertRaises(
            ConfigurationError, collection.insert, {}, safe=True)

        done()

    @async_test_engine()
    def test_slave_okay(self, done):
        # Motor doesn't support 'slave_okay'
        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, slave_okay=True)

        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, slave_okay=False)

        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, slaveok=True)

        self.assertRaises(
            ConfigurationError, motor.MotorClient, host, port, slaveok=False)

        cx = motor.MotorClient(host, port)
        yield motor.Op(cx.open)
        collection = cx.pymongo_test.test_collection

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slave_okay=True)

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slaveok=True)

        done()