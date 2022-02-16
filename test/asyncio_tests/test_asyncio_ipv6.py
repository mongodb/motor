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

"""Test AsyncIOMotorClient with IPv6."""

import test
import unittest
from test import SkipTest
from test.asyncio_tests import AsyncIOTestCase, asyncio_test
from test.test_environment import connected, db_password, db_user, env

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


class MotorIPv6Test(AsyncIOTestCase):
    @asyncio_test
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

        cx = self.asyncio_client(uri=cx_string)
        collection = cx.motor_test.test_collection
        await collection.insert_one({"dummy": "object"})
        self.assertTrue((await collection.find_one({"dummy": "object"})))


if __name__ == "__main__":
    unittest.main()
