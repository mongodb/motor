
"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

import pymongo
from bson import objectid
from tornado import gen
from tornado.testing import gen_test

import motor
from test import MotorTest, AssertEqual


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
    def setUp(self):
        super(SONManipulatorTest, self).setUp()
        self.sync_db.son_manipulator_test_collection.drop()
        self.coll = self.cx.pymongo_test.son_manipulator_test_collection

    def tearDown(self):
        self.sync_db.son_manipulator_test_collection.drop()
        super(SONManipulatorTest, self).tearDown()

    @gen_test
    def test_with_find_one(self):
        coll = self.coll
        _id = yield coll.insert({'foo': 'bar'})
        yield AssertEqual(
            {'_id': _id, 'foo': 'bar'},
            coll.find_one)
        # add SONManipulator and test again
        coll.database.add_son_manipulator(CustomSONManipulator())
        yield AssertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            coll.find_one)

    @gen_test
    def test_with_fetch_next(self):
        coll = self.coll
        coll.database.add_son_manipulator(CustomSONManipulator())
        _id = yield coll.insert({'foo': 'bar'})
        cursor = coll.find()
        self.assertTrue((yield cursor.fetch_next))
        self.assertEqual(
            {'_id': _id, 'foo': 'bar', 'added_field': 42},
            cursor.next_object())

    @gen_test
    def test_with_to_list(self):
        coll = self.coll
        _id1, _id2 = yield coll.insert([{}, {}])
        found = yield coll.find().sort([('_id', pymongo.ASCENDING)]).to_list(length=2)
        self.assertEqual([{'_id': _id1}, {'_id': _id2}], found)

        coll.database.add_son_manipulator(CustomSONManipulator())
        expected = [{'_id': _id1, 'added_field': 42}, {'_id': _id2, 'added_field': 42}]
        found = yield coll.find().sort([('_id', pymongo.ASCENDING)]).to_list(length=2)
        self.assertEqual(expected, found)
        found = yield coll.find().sort([('_id', pymongo.ASCENDING)]).to_list(length=None)
        self.assertEqual(expected, found)
