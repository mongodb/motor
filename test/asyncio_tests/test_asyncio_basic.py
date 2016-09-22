# Copyright 2013-2015 MongoDB, Inc.
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

from __future__ import unicode_literals, absolute_import

from unittest import SkipTest

import pymongo
from pymongo.errors import ConfigurationError
from pymongo.read_preferences import ReadPreference
from motor import motor_asyncio

import test
from test.asyncio_tests import asyncio_test, AsyncIOTestCase
from test.utils import ignore_deprecations


class AIOMotorTestBasic(AsyncIOTestCase):
    def test_repr(self):
        self.assertTrue(repr(self.cx).startswith('MotorClient'))
        self.assertTrue(repr(self.db).startswith('MotorDatabase'))
        self.assertTrue(repr(self.collection).startswith('MotorCollection'))
        cursor = self.collection.find()
        self.assertTrue(repr(cursor).startswith('MotorCursor'))

    @asyncio_test(timeout=30)
    def test_write_concern(self):
        # Default empty dict means "w=1"
        self.assertEqual({}, self.cx.write_concern)

        yield from self.collection.remove()
        yield from self.collection.insert({'_id': 0})

        for gle_options in [
            {},
            {'w': 0},
            {'w': 1},
            {'wtimeout': 1000},
        ]:
            cx = self.asyncio_client(test.env.uri, **gle_options)
            expected_wc = gle_options.copy()
            self.assertEqual(expected_wc, cx.write_concern)

            db = cx.motor_test
            self.assertEqual(expected_wc, db.write_concern)

            collection = db.test_collection
            self.assertEqual(expected_wc, collection.write_concern)

            if gle_options.get('w') == 0:
                yield from collection.insert({'_id': 0})  # No error
            else:
                with self.assertRaises(pymongo.errors.DuplicateKeyError):
                    yield from collection.insert({'_id': 0})

            # No error
            yield from collection.insert({'_id': 0}, w=0)
            cx.close()

        collection = self.db.test_collection
        collection.write_concern['w'] = 2

        # No error
        yield from collection.insert({'_id': 0}, w=0)

        cxw2 = self.asyncio_client(w=2)
        yield from cxw2.motor_test.test_collection.insert({'_id': 0}, w=0)

        # Test write concerns passed to MotorClient, set on collection, or
        # passed to insert.
        if test.env.is_replica_set:
            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield from cxw2.motor_test.test_collection.insert({'_id': 0})

            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield from collection.insert({'_id': 0})

            with self.assertRaises(pymongo.errors.DuplicateKeyError):
                yield from self.collection.insert({'_id': 0}, w=2)
        else:
            # w > 1 and no replica set
            with self.assertRaises(pymongo.errors.OperationFailure):
                yield from cxw2.motor_test.test_collection.insert({'_id': 0})

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield from collection.insert({'_id': 0})

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield from self.collection.insert({'_id': 0}, w=2)

        # Important that the last operation on each MotorClient was
        # acknowledged, so lingering messages aren't delivered in the middle of
        # the next test. Also, a quirk of tornado.testing.AsyncTestCase:  we
        # must relinquish all file descriptors before its tearDown calls
        # self.loop.close(all_fds=True).
        cxw2.close()

    @asyncio_test
    @ignore_deprecations
    def test_read_preference(self):
        # Check the default
        cx = motor_asyncio.AsyncIOMotorClient(test.env.uri, io_loop=self.loop)
        self.assertEqual(ReadPreference.PRIMARY, cx.read_preference)

        # We can set mode, tags, and latency.
        cx = self.asyncio_client(
            read_preference=ReadPreference.SECONDARY,
            tag_sets=[{'foo': 'bar'}],
            secondary_acceptable_latency_ms=42)

        self.assertEqual(ReadPreference.SECONDARY, cx.read_preference)
        self.assertEqual([{'foo': 'bar'}], cx.tag_sets)
        self.assertEqual(42, cx.secondary_acceptable_latency_ms)

        # Make a MotorCursor and get its PyMongo Cursor
        motor_cursor = cx.motor_test.test_collection.find(
            io_loop=self.loop,
            read_preference=ReadPreference.NEAREST,
            tag_sets=[{'yay': 'jesse'}],
            secondary_acceptable_latency_ms=17)

        cursor = motor_cursor.delegate

        self.assertEqual(
            ReadPreference.NEAREST, cursor._Cursor__read_preference)

        self.assertEqual([{'yay': 'jesse'}], cursor._Cursor__tag_sets)
        self.assertEqual(17, cursor._Cursor__secondary_acceptable_latency_ms)

        cx.close()

    @asyncio_test
    def test_safe(self):
        # Motor doesn't support 'safe'
        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri, io_loop=self.loop,
            safe=True)

        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri, io_loop=self.loop,
            safe=False)

        self.assertRaises(
            ConfigurationError, self.collection.insert, {}, safe=False)

        self.assertRaises(
            ConfigurationError, self.collection.insert, {}, safe=True)

    @asyncio_test
    def test_slave_okay(self):
        # Motor doesn't support 'slave_okay'
        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri,
            io_loop=self.loop, slave_okay=True)

        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri,
            io_loop=self.loop, slave_okay=False)

        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri,
            io_loop=self.loop, slaveok=True)

        self.assertRaises(
            ConfigurationError,
            motor_asyncio.AsyncIOMotorClient, test.env.uri,
            io_loop=self.loop, slaveok=False)

        collection = self.cx.motor_test.test_collection

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slave_okay=True)

        self.assertRaises(
            ConfigurationError,
            collection.find_one, slaveok=True)

    def test_underscore(self):
        self.assertIsInstance(self.cx['_db'],
                              motor_asyncio.AsyncIOMotorDatabase)
        self.assertIsInstance(self.db['_collection'],
                              motor_asyncio.AsyncIOMotorCollection)
        self.assertIsInstance(self.collection['_collection'],
                              motor_asyncio.AsyncIOMotorCollection)

        with self.assertRaises(AttributeError):
            self.cx._db

        with self.assertRaises(AttributeError):
            self.db._collection

        with self.assertRaises(AttributeError):
            self.collection._collection

    def test_abc(self):
        try:
            from abc import ABC
        except ImportError:
            # Python < 3.4.
            raise SkipTest()

        class C(ABC):
            db = self.db
            collection = self.collection
            subcollection = self.collection.subcollection

        # MOTOR-104, TypeError: Can't instantiate abstract class C with abstract
        # methods collection, db, subcollection.
        C()
