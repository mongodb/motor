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

import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import iostream, gen
from tornado.testing import gen_test

import motor
import test
from test import host, port, MotorReplicaSetTestBase, assert_raises, MotorTest
from test import SkipTest


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @gen_test
    def test_replica_set_client(self):
        cx = self.motor_rsc()
        self.assertEqual(cx, (yield cx.open()))
        self.assertEqual(cx, (yield cx.open()))  # Same the second time.
        self.assertTrue(isinstance(
            cx.delegate._MongoReplicaSetClient__monitor,
            motor.MotorReplicaSetMonitor))

        self.assertEqual(
            self.io_loop,
            cx.delegate._MongoReplicaSetClient__monitor.io_loop)

        cx.close()

    @gen_test
    def test_open_callback(self):
        yield self.check_optional_callback(self.rsc.open)

    def test_io_loop(self):
        with assert_raises(TypeError):
            motor.MotorReplicaSetClient(test.env.rs_uri, io_loop='foo')

    @gen_test
    def test_auto_reconnect_exception_when_read_preference_is_secondary(self):
        old_write = iostream.IOStream.write
        iostream.IOStream.write = lambda self, data: self.close()

        try:
            cursor = self.rsc.motor_test.test_collection.find(
                read_preference=pymongo.ReadPreference.SECONDARY)

            with assert_raises(pymongo.errors.AutoReconnect):
                yield cursor.fetch_next
        finally:
            iostream.IOStream.write = old_write

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorReplicaSetClient(
            'localhost:8765', replicaSet='rs', io_loop=self.io_loop)

        # Test the Future interface.
        with assert_raises(pymongo.errors.ConnectionFailure):
            yield client.open()

        # Test with a callback.
        (result, error), _ = yield gen.Task(client.open)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, pymongo.errors.ConnectionFailure))

    @gen_test
    def test_socketKeepAlive(self):
        # Connect.
        yield self.rsc.server_info()
        self.assertFalse(self.rsc._get_primary_pool().socket_keepalive)

        client = self.motor_rsc(socketKeepAlive=True)
        yield client.server_info()
        self.assertTrue(client._get_primary_pool().socket_keepalive)


class TestReplicaSetClientAgainstStandalone(MotorTest):
    """This is a funny beast -- we want to run tests for MotorReplicaSetClient
    but only if the database at DB_IP and DB_PORT is a standalone.
    """
    def setUp(self):
        super(TestReplicaSetClientAgainstStandalone, self).setUp()
        if test.env.is_replica_set:
            raise SkipTest(
                "Connected to a replica set, not a standalone mongod")

    @gen_test
    def test_connect(self):
        with assert_raises(pymongo.errors.ConnectionFailure):
            yield motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet='anything',
                connectTimeoutMS=600).test.test.find_one()


if __name__ == '__main__':
    unittest.main()
