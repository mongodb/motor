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
import warnings

import pymongo.errors
from tornado.testing import gen_test

import motor
from test import MotorTest, assert_raises


class MotorGenTest(MotorTest):
    @gen_test
    def test_op(self):
        # motor.Op is deprecated in Motor 0.2, superseded by Tornado 3 Futures.
        # Just make sure it still works.

        collection = self.collection
        doc = {'_id': 'jesse'}

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Op works.
            _id = yield motor.Op(collection.insert, doc)
            self.assertEqual('jesse', _id)

            # Raised a DeprecationWarning.
            self.assertEqual(1, len(w))
            warning = w[-1]
            self.assertTrue(issubclass(warning.category, DeprecationWarning))
            message = str(warning.message)
            self.assertTrue("deprecated" in message)
            self.assertTrue("insert" in message)

        result = yield motor.Op(collection.find_one, doc)
        self.assertEqual(doc, result)

        # Make sure it works with no args.
        result = yield motor.Op(collection.find_one)
        self.assertTrue(isinstance(result, dict))

        with assert_raises(pymongo.errors.DuplicateKeyError):
            yield motor.Op(collection.insert, doc)


if __name__ == '__main__':
    unittest.main()
