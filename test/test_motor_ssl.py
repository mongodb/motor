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
from pymongo.errors import ConfigurationError
from tornado.testing import gen_test

import motor
from test import host, port, MotorTest, HAVE_SSL


class MotorNoSSLTest(MotorTest):
    def test_no_ssl(self):
        if HAVE_SSL:
            raise SkipTest(
                "We have SSL compiled into Python, can't test what happens "
                "without SSL")

        for cx_class in (
            motor.MotorClient,
            motor.MotorReplicaSetClient
        ):
            self.assertRaises(
                ConfigurationError,
                cx_class(host, port, ssl=True, io_loop=self.io_loop).open_sync)


class MotorSSLTest(MotorTest):
    ssl = True

    @gen_test
    def test_simple_ops(self):
        if not HAVE_SSL:
            raise SkipTest("SSL not compiled into Python")

        cx = self.motor_client(ssl=True)

        # Make sure the client works
        collection = cx.motor_test.test_collection
        doc = yield collection.find_one({'_id': 0})
        self.assertEqual(0, doc['_id'])


if __name__ == '__main__':
    unittest.main()
