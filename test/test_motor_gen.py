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

from pymongo.errors import DuplicateKeyError
from tornado.testing import gen_test

import motor
from test import MotorTest


class MotorGenTest(MotorTest):
    def tearDown(self):
        self.sync_db.test_collection2.drop()
        super(MotorGenTest, self).tearDown()

    @gen_test
    def test_op(self):
        collection = self.cx.pymongo_test.test_collection
        doc = {'_id': 'jesse'}
        _id = yield motor.Op(collection.insert, doc)
        self.assertEqual('jesse', _id)
        result = yield motor.Op(collection.find_one, doc)
        self.assertEqual(doc, result)

        error = None
        try:
            yield motor.Op(collection.insert, doc)
        except Exception, e:
            error = e

        self.assertTrue(isinstance(error, DuplicateKeyError))


if __name__ == '__main__':
    unittest.main()
