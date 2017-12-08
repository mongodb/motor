# Copyright 2013-2015 MongoDB, Inc.
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

import pymongo.son_manipulator
from tornado.testing import gen_test

from test import env, SkipTest
from test.tornado_tests import MotorTest
from test.utils import ignore_deprecations


class CustomSONManipulator(pymongo.son_manipulator.SONManipulator):
    """A pymongo outgoing SON Manipulator that adds
    ``{'added_field' : 42}``
    """
    def will_copy(self):
        return False

    def transform_outgoing(self, son, collection):
        assert 'added_field' not in son
        son['added_field'] = 42
        return son


class SONManipulatorTest(MotorTest):
    def _clear_collection(self):
        env.sync_cx.motor_test.son_manipulator_test_collection.delete_many({})

    def setUp(self):
        super(SONManipulatorTest, self).setUp()
        self._clear_collection()

    def tearDown(self):
        self._clear_collection()
        super(SONManipulatorTest, self).tearDown()

    @ignore_deprecations
    @gen_test
    def test_with_find_one(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id = yield coll.insert({'foo': 'bar'})
        self.assertEqual(
            {'_id': _id, 'foo': 'bar'},
            (yield coll.find_one()))

        # Add SONManipulator and test again.
        coll.database.add_son_manipulator(CustomSONManipulator())
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            (yield coll.find_one()))

    @ignore_deprecations
    @gen_test
    def test_with_fetch_next(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        coll.database.add_son_manipulator(CustomSONManipulator())
        _id = yield coll.insert({'foo': 'bar'})
        cursor = coll.find()
        self.assertTrue((yield cursor.fetch_next))
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            cursor.next_object())

        yield cursor.close()

    @ignore_deprecations
    @gen_test
    def test_with_to_list(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id1, _id2 = yield coll.insert([{}, {}])
        found = yield coll.find().sort([('_id', 1)]).to_list(length=2)
        self.assertEqual([{'_id': _id1}, {'_id': _id2}], found)

        coll.database.add_son_manipulator(CustomSONManipulator())
        expected = [
            {'_id': _id1, 'added_field': 42},
            {'_id': _id2, 'added_field': 42}]

        cursor = coll.find().sort([('_id', 1)])
        found = yield cursor.to_list(length=2)
        self.assertEqual(expected, found)
        yield cursor.close()

    @ignore_deprecations
    @gen_test
    def test_with_aggregate(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id = yield coll.insert({'foo': 'bar'})
        coll.database.add_son_manipulator(CustomSONManipulator())

        # Test aggregation cursor, both with fetch_next and to_list.
        cursor = coll.aggregate([])
        assert (yield cursor.fetch_next)
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            cursor.next_object())

        cursor = coll.aggregate([])
        self.assertEqual(
            [{'_id': _id, 'foo': 'bar', 'added_field': 42}],
            (yield cursor.to_list(length=None)))
