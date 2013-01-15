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

from nose.plugins.skip import SkipTest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

import motor
from test import host, port
from test import MotorTest, async_test_engine


class MotorIPv6Test(MotorTest):
    @async_test_engine()
    def test_ipv6(self, done):
        assert host in ('localhost', '127.0.0.1'), (
            "This unittest isn't written to test IPv6 with host %s" % repr(host)
        )

        try:
            MongoClient("[::1]")
        except ConnectionFailure:
            # Either mongod was started without --ipv6
            # or the OS doesn't support it (or both).
            raise SkipTest("No IPV6")

        # Make sure we can connect over IPv6 using both open() and open_sync()
        for open_sync in (True, False):
            cx_string = "mongodb://[::1]:%d" % port
            cx = motor.MotorClient(cx_string)
            if open_sync:
                cx.open_sync()
            else:
                yield motor.Op(cx.open)

            yield motor.Op(
                cx.pymongo_test.pymongo_test.insert, {"dummy": "object"})
            result = yield motor.Op(
                cx.pymongo_test.pymongo_test.find_one, {"dummy": "object"})
            self.assertEqual('object', result['dummy'])

        done()

if __name__ == '__main__':
    unittest.main()
