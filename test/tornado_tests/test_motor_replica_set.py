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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

import pymongo
import pymongo.auth
import pymongo.errors
import pymongo.mongo_replica_set_client
from bson.binary import JAVA_LEGACY, UUID_SUBTYPE
from tornado import gen
from tornado.testing import gen_test

import motor
import motor.core
import test
from test import SkipTest
from test.test_environment import db_user, db_password, env
from test.tornado_tests import MotorReplicaSetTestBase, MotorTest
from test.utils import one, ignore_deprecations

from motor.motor_py3_compat import text_type


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    @gen_test
    def test_replica_set_client(self):
        cx = self.motor_rsc()
        self.assertEqual(cx, (yield cx.open()))
        self.assertEqual(cx, (yield cx.open()))  # Same the second time.
        cx.close()

    @gen_test
    def test_open_callback(self):
        yield self.check_optional_callback(self.rsc.open)

    def test_io_loop(self):
        with self.assertRaises(TypeError):
            motor.MotorReplicaSetClient(test.env.rs_uri, io_loop='foo')

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorReplicaSetClient(
            'localhost:8765', replicaSet='rs', io_loop=self.io_loop)

        with ignore_deprecations():
            # Test the Future interface.
            with self.assertRaises(pymongo.errors.ConnectionFailure):
                yield client.open()

            # Test with a callback.
            (result, error), _ = yield gen.Task(client.open)

        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, pymongo.errors.ConnectionFailure))

    @gen_test
    def test_socketKeepAlive(self):
        # Connect.
        yield self.rsc.server_info()
        ka = self.rsc._get_primary_pool().socket_keepalive
        self.assertFalse(ka)

        client = self.motor_rsc(socketKeepAlive=True)
        yield client.server_info()
        ka = client._get_primary_pool().socket_keepalive
        self.assertTrue(ka)

    @gen_test
    def test_auth_network_error(self):
        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # Make sure there's no semaphore leak if we get a network error
        # when authenticating a new socket with cached credentials.
        # Get a client with one socket so we detect if it's leaked.
        c = self.motor_rsc(max_pool_size=1, waitQueueTimeoutMS=1)
        yield c.open()

        # Simulate an authenticate() call on a different socket.
        credentials = pymongo.auth._build_credentials_tuple(
            'DEFAULT', 'admin',
            text_type(db_user), text_type(db_password),
            {})

        c.delegate._cache_credentials('test', credentials, connect=False)

        # Cause a network error on the actual socket.
        pool = c._get_primary_pool()
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

    def test_uuid_subtype(self):
        if pymongo.version_tuple < (2, 9, 4):
            raise SkipTest("PYTHON-1145")

        cx = self.motor_rsc(uuidRepresentation='javaLegacy')

        with ignore_deprecations():
            self.assertEqual(cx.uuid_subtype, JAVA_LEGACY)
            cx.uuid_subtype = UUID_SUBTYPE
            self.assertEqual(cx.uuid_subtype, UUID_SUBTYPE)
            self.assertEqual(cx.delegate.uuid_subtype, UUID_SUBTYPE)


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
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield motor.MotorReplicaSetClient(
                '%s:%s' % (env.host, env.port), replicaSet='anything',
                io_loop=self.io_loop,
                connectTimeoutMS=600).test.test.find_one()


if __name__ == '__main__':
    unittest.main()
