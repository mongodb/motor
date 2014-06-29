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

from __future__ import unicode_literals

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from tornado.testing import gen_test

import motor
import test
from test import host, port, MotorTest, SkipTest


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

        if test.env.auth:
            cx_string = 'mongodb://%s:%s@[::1]:%d' % (
                test.db_user, test.db_password, port)
        else:
            cx_string = 'mongodb://[::1]:%d' % port

        cx = motor.MotorClient(cx_string, io_loop=self.io_loop)
        collection = cx.motor_test.test_collection
        yield collection.insert({"dummy": "object"})
        self.assertTrue((yield collection.find_one({"dummy": "object"})))


if __name__ == '__main__':
    unittest.main()
