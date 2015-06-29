# Copyright 2014 MongoDB, Inc.
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

"""Test AsyncIOReplicaSetClient."""

import unittest

import pymongo.errors
import pymongo.mongo_replica_set_client

import test
from motor import motor_asyncio
from test import SkipTest
from test.asyncio_tests import (asyncio_client_test_generic,
                                AsyncIOTestCase,
                                asyncio_test)
from test.test_environment import port, host, env


class TestAsyncIOReplicaSet(AsyncIOTestCase):
    def setUp(self):
        if not test.env.is_replica_set:
            raise SkipTest('Not connected to a replica set')

        super().setUp()

    @asyncio_test
    def test_replica_set_client(self):
        cx = self.asyncio_rsc()
        self.assertEqual(cx, (yield from cx.open()))
        self.assertEqual(cx, (yield from cx.open()))  # Same the second time.

    @asyncio_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port.
        client = motor_asyncio.AsyncIOMotorReplicaSetClient(
            'localhost:8765', replicaSet='rs', io_loop=self.loop)

        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield from client.open()


class AsyncIOReplicaSetClientTestGeneric(
        asyncio_client_test_generic.AsyncIOClientTestMixin,
        AsyncIOTestCase):

    def setUp(self):
        if not test.env.is_replica_set:
            raise SkipTest('Not connected to a replica set')

        super().setUp()

    def get_client(self, *args, **kwargs):
        return self.asyncio_rsc(
            env.uri, *args, replicaSet=env.rs_name, **kwargs)


class TestReplicaSetClientAgainstStandalone(AsyncIOTestCase):
    """This is a funny beast -- we want to run tests for MotorReplicaSetClient
    but only if the database at DB_IP and DB_PORT is a standalone.
    """
    def setUp(self):
        super(TestReplicaSetClientAgainstStandalone, self).setUp()
        if test.env.is_replica_set:
            raise SkipTest(
                "Connected to a replica set, not a standalone mongod")

    @asyncio_test
    def test_connect(self):
        client = motor_asyncio.AsyncIOMotorReplicaSetClient(
            '%s:%s' % (host, port), replicaSet='anything',
            connectTimeoutMS=600, io_loop=self.loop)

        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield from client.test.test.find_one()


if __name__ == '__main__':
    unittest.main()
