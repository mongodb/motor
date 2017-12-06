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

"""Test replica set MotorClient."""

import unittest

import pymongo
import pymongo.auth
import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import gen
from tornado.testing import gen_test

import motor
import motor.core
import test
from test import SkipTest
from test.test_environment import db_user, db_password, env
from test.tornado_tests import MotorReplicaSetTestBase, MotorTest
from test.utils import one, get_primary_pool

from motor.motor_py3_compat import text_type


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    def test_io_loop(self):
        with self.assertRaises(TypeError):
            motor.MotorClient(test.env.rs_uri, io_loop='foo')

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorClient(
            'localhost:8765', replicaSet='rs', io_loop=self.io_loop,
            serverSelectionTimeoutMS=10)

        # Test the Future interface.
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield client.admin.command('ismaster')

        # Test with a callback.
        (result, error), _ = yield gen.Task(client.admin.command, 'ismaster')
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, pymongo.errors.ConnectionFailure))

    @gen_test
    def test_socketKeepAlive(self):
        # Connect.
        yield self.rsc.server_info()
        ka = get_primary_pool(self.rsc).opts.socket_keepalive
        self.assertTrue(ka)

        client = self.motor_rsc(socketKeepAlive=False)
        yield client.server_info()
        ka = get_primary_pool(client).opts.socket_keepalive
        self.assertFalse(ka)

    @gen_test
    def test_auth_network_error(self):
        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # Make sure there's no semaphore leak if we get a network error
        # when authenticating a new socket with cached credentials.
        # Get a client with one socket so we detect if it's leaked.
        c = self.motor_rsc(maxPoolSize=1, waitQueueTimeoutMS=1)
        yield c.admin.command('ismaster')

        # Simulate an authenticate() call on a different socket.
        credentials = pymongo.auth._build_credentials_tuple(
            'DEFAULT', 'admin',
            text_type(db_user), text_type(db_password),
            {})

        c.delegate._cache_credentials('test', credentials, connect=False)

        # Cause a network error on the actual socket.
        pool = get_primary_pool(c)
        socket_info = one(pool.sockets)
        socket_info.sock.close()

        # In __check_auth, the client authenticates its socket with the
        # new credential, but gets a socket.error. Should be reraised as
        # AutoReconnect.
        with self.assertRaises(pymongo.errors.AutoReconnect):
            yield c.test.collection.find_one()

        # No semaphore leak, the pool is allowed to make a new socket.
        yield c.test.collection.find_one()

    @gen_test
    def test_open_concurrent(self):
        # MOTOR-66: don't block on PyMongo's __monitor_lock, but also don't
        # spawn multiple monitors.
        c = self.motor_rsc()
        yield [c.db.collection.find_one(), c.db.collection.find_one()]


class TestReplicaSetClientAgainstStandalone(MotorTest):
    """This is a funny beast -- we want to run tests for a replica set
    MotorClient but only if the database at DB_IP and DB_PORT is a standalone.
    """
    def setUp(self):
        super(TestReplicaSetClientAgainstStandalone, self).setUp()
        if test.env.is_replica_set:
            raise SkipTest(
                "Connected to a replica set, not a standalone mongod")

    @gen_test
    def test_connect(self):
        with self.assertRaises(pymongo.errors.ServerSelectionTimeoutError):
            yield motor.MotorClient(
                '%s:%s' % (env.host, env.port), replicaSet='anything',
                io_loop=self.io_loop,
                serverSelectionTimeoutMS=10).test.test.find_one()


if __name__ == '__main__':
    unittest.main()
