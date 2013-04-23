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
from tornado import iostream
from tornado.testing import gen_test

import motor
from test import host, port, MotorReplicaSetTestBase, assert_raises


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @gen_test
    def test_replica_set_client(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name, io_loop=self.io_loop)

        # Can't access databases before connecting
        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx.some_database_name
        )

        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx['some_database_name']
        )

        result = yield cx.open()
        self.assertEqual(result, cx)
        self.assertTrue(cx.connected)
        self.assertTrue(isinstance(
            cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))

        self.assertEqual(
            self.io_loop,
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)

    @gen_test
    def test_open_callback(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name, io_loop=self.io_loop)
        yield self.check_optional_callback(cx.open)
        cx.close()

    def test_io_loop(self):
        with assert_raises(TypeError):
            motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet=self.name, io_loop='foo')

    @gen_test
    def test_open_sync(self):
        cx = motor.MotorReplicaSetClient(
            host, port, replicaSet=self.name, io_loop=self.io_loop)

        self.assertFalse(cx.connected)

        # open_sync() creates a special IOLoop just to run the connection
        # code to completion
        self.assertEqual(cx, cx.open_sync())
        self.assertTrue(cx.connected)

        # IOLoop was restored?
        self.assertEqual(self.io_loop, cx.io_loop)

        # Really connected?
        result = yield motor.Op(
            cx.pymongo_test.test_collection.find_one, {'_id': 0})

        self.assertEqual(0, result['_id'])
        cx.close()

    @gen_test
    def test_sync_client(self):
        class DictSubclass(dict):
            pass

        args = ['%s:%s' % (host, port)]
        kwargs = dict(
            connectTimeoutMS=1000, socketTimeoutMS=1500, max_pool_size=23,
            document_class=DictSubclass, tz_aware=True, replicaSet=self.name,
            io_loop=self.io_loop)

        cx = yield motor.Op(motor.MotorReplicaSetClient(
            *args, **kwargs).open)
        sync_cx = cx.sync_client()
        self.assertTrue(isinstance(
            sync_cx, pymongo.mongo_replica_set_client.MongoReplicaSetClient))
        self.assertFalse(isinstance(
            sync_cx._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))
        self.assertEqual(
            1000,
            sync_cx._MongoReplicaSetClient__conn_timeout * 1000.0)
        self.assertEqual(
            1500,
            sync_cx._MongoReplicaSetClient__net_timeout * 1000.0)
        self.assertEqual(23, sync_cx.max_pool_size)
        self.assertEqual(True, sync_cx._MongoReplicaSetClient__tz_aware)
        self.assertEqual(
            DictSubclass,
            sync_cx._MongoReplicaSetClient__document_class)

        # Make sure sync client works
        self.assertEqual(
            {'_id': 5, 's': hex(5)},
            sync_cx.pymongo_test.test_collection.find_one({'_id': 5}))

    @gen_test
    def test_auto_reconnect_exception_when_read_preference_is_secondary(self):
        old_write = iostream.IOStream.write
        iostream.IOStream.write = lambda self, data: self.close()

        try:
            cursor = self.rsc.pymongo_test.test_collection.find(
                read_preference=pymongo.ReadPreference.SECONDARY)

            with assert_raises(pymongo.errors.AutoReconnect):
                yield cursor.fetch_next
        finally:
            iostream.IOStream.write = old_write


if __name__ == '__main__':
    unittest.main()
