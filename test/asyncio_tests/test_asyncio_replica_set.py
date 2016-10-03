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

import pymongo
import pymongo.errors
import pymongo.mongo_replica_set_client
from bson.binary import JAVA_LEGACY, UUID_SUBTYPE

import test
from motor import motor_asyncio
from test import env, SkipTest
from test.asyncio_tests import AsyncIOTestCase, asyncio_test
from test.utils import ignore_deprecations


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
            yield from client.admin.command('ping')

    @unittest.skipIf(pymongo.version_tuple < (2, 9, 4), "PYTHON-1145")
    def test_uuid_subtype(self):
        cx = self.asyncio_rsc(uuidRepresentation='javaLegacy')

        with ignore_deprecations():
            self.assertEqual(cx.uuid_subtype, JAVA_LEGACY)
            cx.uuid_subtype = UUID_SUBTYPE
            self.assertEqual(cx.uuid_subtype, UUID_SUBTYPE)
            self.assertEqual(cx.delegate.uuid_subtype, UUID_SUBTYPE)


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
            '%s:%s' % (env.host, env.port), replicaSet='anything',
            connectTimeoutMS=600, io_loop=self.loop)

        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield from client.test.test.find_one()


if __name__ == '__main__':
    unittest.main()
