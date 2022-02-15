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

"""Test replica set MotorClient."""

import test
import unittest
from test import SkipTest
from test.test_environment import env
from test.tornado_tests import MotorReplicaSetTestBase, MotorTest

import pymongo
import pymongo.auth
import pymongo.errors
from tornado import gen
from tornado.testing import gen_test

import motor
import motor.core


class MotorReplicaSetTest(MotorReplicaSetTestBase):
    def test_io_loop(self):
        with self.assertRaises(TypeError):
            motor.MotorClient(test.env.rs_uri, io_loop="foo")

    @gen_test
    async def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorClient(
            "localhost:8765", replicaSet="rs", io_loop=self.io_loop, serverSelectionTimeoutMS=10
        )

        # Test the Future interface.
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            await client.admin.command("ismaster")

    @gen_test
    async def test_open_concurrent(self):
        # MOTOR-66: don't block on PyMongo's __monitor_lock, but also don't
        # spawn multiple monitors.
        c = self.motor_rsc()
        await gen.multi([c.db.collection.find_one(), c.db.collection.find_one()])


class TestReplicaSetClientAgainstStandalone(MotorTest):
    """This is a funny beast -- we want to run tests for a replica set
    MotorClient but only if the database at DB_IP and DB_PORT is a standalone.
    """

    def setUp(self):
        super().setUp()
        if test.env.is_replica_set:
            raise SkipTest("Connected to a replica set, not a standalone mongod")

    @gen_test
    async def test_connect(self):
        with self.assertRaises(pymongo.errors.ServerSelectionTimeoutError):
            await motor.MotorClient(
                "%s:%s" % (env.host, env.port),
                replicaSet="anything",
                io_loop=self.io_loop,
                serverSelectionTimeoutMS=10,
            ).test.test.find_one()


if __name__ == "__main__":
    unittest.main()
