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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import test
import unittest
from test import SkipTest
from test.test_environment import connected, db_password, db_user, env
from test.tornado_tests import MotorTest

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from tornado.testing import gen_test

import motor


class MotorIPv6Test(MotorTest):
    @gen_test
    async def test_ipv6(self):
        assert env.host in (
            "localhost",
            "127.0.0.1",
        ), "This unittest isn't written to test IPv6 with host %s" % repr(env.host)

        try:
            connected(
                MongoClient(
                    "[::1]", username=db_user, password=db_password, serverSelectionTimeoutMS=100
                )
            )
        except ConnectionFailure:
            # Either mongod was started without --ipv6
            # or the OS doesn't support it (or both).
            raise SkipTest("No IPV6")

        if test.env.auth:
            cx_string = "mongodb://%s:%s@[::1]:%d" % (db_user, db_password, env.port)
        else:
            cx_string = "mongodb://[::1]:%d" % env.port

        cx = motor.MotorClient(cx_string, io_loop=self.io_loop)
        collection = cx.motor_test.test_collection
        await collection.insert_one({"dummy": "object"})
        self.assertTrue((await collection.find_one({"dummy": "object"})))


if __name__ == "__main__":
    unittest.main()
