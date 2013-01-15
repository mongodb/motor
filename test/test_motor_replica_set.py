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

import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import ioloop, iostream

import motor
from test import host, port, MotorReplicaSetTestBase
from test import async_test_engine, AssertEqual, AssertRaises


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @async_test_engine()
    def test_replica_set_connection(self, done):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name)

        # Can't access databases before connecting
        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx.some_database_name
        )

        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx['some_database_name']
        )

        result = yield motor.Op(cx.open)
        self.assertEqual(result, cx)
        self.assertTrue(cx.connected)
        self.assertTrue(isinstance(cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))
        self.assertEqual(ioloop.IOLoop.instance(),
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)
        done()

    def test_connection_callback(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name)
        self.check_optional_callback(cx.open)

    @async_test_engine()
    def test_open_sync(self, done):
        loop = ioloop.IOLoop.instance()
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name)
        self.assertFalse(cx.connected)

        # open_sync() creates a special IOLoop just to run the connection
        # code to completion
        self.assertEqual(cx, cx.open_sync())
        self.assertTrue(cx.connected)

        # IOLoop was restored?
        self.assertEqual(loop, cx.io_loop)
        self.assertTrue(isinstance(cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))
        self.assertEqual(loop,
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)

        # Really connected?
        result = yield motor.Op(cx.admin.command, "buildinfo")
        self.assertEqual(int, type(result['bits']))

        yield motor.Op(cx.pymongo_test.test_collection.insert,
            {'_id': 'test_open_sync'})
        doc = yield motor.Op(
            cx.pymongo_test.test_collection.find_one, {'_id': 'test_open_sync'})
        self.assertEqual('test_open_sync', doc['_id'])
        done()

    def test_open_sync_custom_io_loop(self):
        # Check that we can create a MotorReplicaSetClient with a custom
        # IOLoop, then call open_sync(), which uses a new loop, and the custom
        # loop is restored.
        loop = ioloop.IOLoop()
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name, io_loop=loop)
        self.assertEqual(cx, cx.open_sync())
        self.assertTrue(cx.connected)

        # Custom loop restored?
        self.assertEqual(loop, cx.io_loop)
        self.assertTrue(isinstance(cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))
        self.assertEqual(loop,
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)

        @async_test_engine(io_loop=loop)
        def test(self, done):
            # Custom loop works?
            yield AssertEqual(
                {'_id': 17, 's': hex(17)},
                cx.pymongo_test.test_collection.find_one, {'_id': 17})

            yield AssertEqual(
                {'_id': 37, 's': hex(37)},
                cx.pymongo_test.test_collection.find_one, {'_id': 37})

            done()

        test(self)

    def test_custom_io_loop(self):
        self.assertRaises(
            TypeError,
            lambda: motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet=self.name, io_loop='foo')
        )

        loop = ioloop.IOLoop()

        @async_test_engine(io_loop=loop)
        def test(self, done):
            # Make sure we can do async things with the custom loop
            cx = motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet=self.name, io_loop=loop)
            yield AssertEqual(cx, cx.open)
            self.assertTrue(cx.connected)
            self.assertTrue(isinstance(
                cx.delegate._MongoReplicaSetClient__monitor,
                motor.MotorReplicaSetMonitor))
            self.assertEqual(loop,
                cx.delegate._MongoReplicaSetClient__monitor.io_loop)

            doc = yield motor.Op(
                cx.pymongo_test.test_collection.find_one, {'_id': 17})
            self.assertEqual({'_id': 17, 's': hex(17)}, doc)
            done()

        test(self)

    @async_test_engine()
    def test_sync_client(self, done):
        class DictSubclass(dict):
            pass

        args = ['%s:%s' % (host, port)]
        kwargs = dict(
            connectTimeoutMS=1000, socketTimeoutMS=1500, max_pool_size=23,
            document_class=DictSubclass, tz_aware=True, replicaSet=self.name)

        cx = yield motor.Op(motor.MotorReplicaSetClient(
            *args, **kwargs).open)
        sync_cx = cx.sync_client()
        self.assertTrue(isinstance(
            sync_cx, pymongo.mongo_replica_set_client.MongoReplicaSetClient))
        self.assertFalse(isinstance(sync_cx._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))
        self.assertEqual(1000,
            sync_cx._MongoReplicaSetClient__conn_timeout * 1000.0)
        self.assertEqual(1500,
            sync_cx._MongoReplicaSetClient__net_timeout * 1000.0)
        self.assertEqual(23, sync_cx.max_pool_size)
        self.assertEqual(True, sync_cx._MongoReplicaSetClient__tz_aware)
        self.assertEqual(DictSubclass,
            sync_cx._MongoReplicaSetClient__document_class)

        # Make sure sync connection works
        self.assertEqual(
            {'_id': 5, 's': hex(5)},
            sync_cx.pymongo_test.test_collection.find_one({'_id': 5}))

        done()

    @async_test_engine()
    def test_auto_reconnect_exception_when_read_preference_is_secondary(
        self, done
    ):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name)

        yield motor.Op(cx.open)
        db = cx.pymongo_test

        old_write = iostream.IOStream.write
        iostream.IOStream.write = lambda self, data, callback: self.close()

        try:
            cursor = db.pymongo_test.find(
                read_preference=pymongo.ReadPreference.SECONDARY)

            yield AssertRaises(pymongo.errors.AutoReconnect, cursor.each)
        finally:
            iostream.IOStream.write = old_write

        done()


if __name__ == '__main__':
    unittest.main()
