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

import motor
from test import host, port, MotorTest, async_test_engine, have_ssl


class MotorNoSSLTest(unittest.TestCase):
    def test_no_ssl(self):
        if have_ssl:
            raise SkipTest(
                "We have SSL compiled into Python, can't test what happens "
                "without SSL"
            )

        for cx_class in (
            motor.MotorClient,
            motor.MotorReplicaSetClient
        ):
            self.assertRaises(
                ConfigurationError,
                cx_class(host, port, ssl=True).open_sync)


class MotorSSLTest(MotorTest):
    ssl = True

    @async_test_engine()
    def test_simple_ops(self, done):
        if not have_ssl:
            raise SkipTest("SSL not compiled into Python")

        cx = yield motor.Op(motor.MotorClient(host, port, ssl=True).open)

        # Make sure the connection works
        db = cx.motor_ssl_test
        yield motor.Op(db.collection.insert, {'hello': 'goodbye'})
        hello = yield motor.Op(db.collection.find_one, {'hello': 'goodbye'})
        self.assertEqual('goodbye', hello['hello'])
        yield motor.Op(cx.drop_database, db)
        done()


if __name__ == '__main__':
    unittest.main()
