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

import pymongo.son_manipulator

from test.asyncio_tests import AsyncIOTestCase, asyncio_test
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


class SONManipulatorTest(AsyncIOTestCase):
    def setUp(self):
        super(SONManipulatorTest, self).setUp()

    def tearDown(self):
        remove_coro = self.db.son_manipulator_test_collection.delete_many({})
        self.loop.run_until_complete(remove_coro)
        super(SONManipulatorTest, self).tearDown()

    @ignore_deprecations
    @asyncio_test
    def test_with_find_one(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        result = yield from coll.insert_one({'foo': 'bar'})
        expected = {'_id': result.inserted_id, 'foo': 'bar'}
        self.assertEqual(expected, (yield from coll.find_one()))

        # Add SONManipulator and test again.
        coll.database.add_son_manipulator(CustomSONManipulator())
        expected = {'_id': result.inserted_id, 'foo': 'bar', 'added_field': 42}
        self.assertEqual(expected, (yield from coll.find_one()))

    @ignore_deprecations
    @asyncio_test
    def test_with_fetch_next(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        coll.database.add_son_manipulator(CustomSONManipulator())
        result = yield from coll.insert_one({'foo': 'bar'})
        cursor = coll.find()
        self.assertTrue((yield from cursor.fetch_next))
        expected = {'_id': result.inserted_id, 'foo': 'bar', 'added_field': 42}
        self.assertEqual(expected, cursor.next_object())

    @ignore_deprecations
    @asyncio_test
    def test_with_to_list(self):
        coll = self.cx.motor_test.son_manipulator_test_collection
        _id1, _id2 = (yield from coll.insert_many([{}, {}])).inserted_ids
        found = yield from coll.find().sort([('_id', 1)]).to_list(length=2)
        self.assertEqual([{'_id': _id1}, {'_id': _id2}], found)

        coll.database.add_son_manipulator(CustomSONManipulator())
        expected = [
            {'_id': _id1, 'added_field': 42},
            {'_id': _id2, 'added_field': 42}]

        cursor = coll.find().sort([('_id', 1)])
        found = yield from cursor.to_list(length=2)
        self.assertEqual(expected, found)
        yield from cursor.close()
