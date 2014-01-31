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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

from nose.plugins.skip import SkipTest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from tornado.testing import gen_test

import motor
from test import host, port, MotorTest


class MotorIPv6Test(MotorTest):
    @gen_test
    def test_ipv6(self):
        assert host in ('localhost', '127.0.0.1'), (
            "This unittest isn't written to test IPv6 with host %s" % repr(host)
        )

        try:
            MongoClient("[::1]")
        except ConnectionFailure:
            # Either mongod was started without --ipv6
            # or the OS doesn't support it (or both).
            raise SkipTest("No IPV6")

        cx_string = "mongodb://[::1]:%d" % port
        cx = motor.MotorClient(cx_string, io_loop=self.io_loop)
        collection = cx.motor_test.test_collection
        yield collection.insert({"dummy": "object"})
        self.assertTrue((yield collection.find_one({"dummy": "object"})))


if __name__ == '__main__':
    unittest.main()
