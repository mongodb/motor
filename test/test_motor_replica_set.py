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
from nose.plugins.skip import SkipTest
from tornado import iostream
from tornado.testing import gen_test

import motor
from test import host, port, MotorReplicaSetTestBase, assert_raises, MotorTest


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @gen_test
    def test_replica_set_client(self):
        cx = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet=self.name, io_loop=self.io_loop)

        self.assertEqual(cx, (yield cx.open()))
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


class TestReplicaSetClientAgainstStandalone(MotorTest):
    """This is a funny beast -- we want to run tests for MotorReplicaSetClient
    but only if the database at DB_IP and DB_PORT is a standalone.
    """
    def setUp(self):
        super(TestReplicaSetClientAgainstStandalone, self).setUp()
        response = self.sync_cx.admin.command('ismaster')
        if 'setName' in response:
            raise SkipTest(
                "Connected to a replica set, not a standalone mongod")

    @gen_test
    def test_connect(self):
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield motor.MotorReplicaSetClient(
                '%s:%s' % (host, port), replicaSet='anything',
                connectTimeoutMS=600).test.test.find_one()


if __name__ == '__main__':
    unittest.main()
