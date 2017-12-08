# Copyright 2012-2015 MongoDB, Inc.
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

import pymongo.database
from bson import CodecOptions
from bson.binary import JAVA_LEGACY
from pymongo import ReadPreference, WriteConcern
from pymongo.read_preferences import Secondary
from pymongo.errors import OperationFailure, CollectionInvalid
from pymongo.son_manipulator import AutoReference, NamespaceInjector
from tornado import gen
from tornado.testing import gen_test

import motor
import test
from test.test_environment import env
from test.tornado_tests import MotorTest, remove_all_users
from test.utils import ignore_deprecations


class MotorDatabaseTest(MotorTest):
    @gen_test
    def test_database(self):
        # Test that we can create a db directly, not just from MotorClient's
        # accessors
        db = motor.MotorDatabase(self.cx, 'motor_test')

        # Make sure we got the right DB and it can do an operation
        self.assertEqual('motor_test', db.name)
        yield db.test_collection.insert_one({'_id': 1})
        doc = yield db.test_collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

    def test_collection_named_delegate(self):
        db = self.db
        self.assertTrue(isinstance(db.delegate, pymongo.database.Database))
        self.assertTrue(isinstance(db['delegate'], motor.MotorCollection))
        db.client.close()

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.cx.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @gen_test
    def test_database_callbacks(self):
        db = self.db
        yield db.drop_collection('c')

        self.assertRaises(TypeError, db.create_collection, 'c', callback='foo')
        self.assertRaises(TypeError, db.create_collection, 'c', callback=1)

        # No error without callback
        db.create_collection('c', callback=None)

        # Wait for create_collection to complete
        for _ in range(10):
            yield gen.sleep(0.1)
            if 'c' in (yield db.collection_names()):
                break

    @gen_test
    def test_command(self):
        result = yield self.cx.admin.command("buildinfo")
        # Make sure we got some sane result or other.
        self.assertEqual(1, result['ok'])

    @gen_test
    def test_create_collection(self):
        # Test creating collection, return val is wrapped in MotorCollection,
        # creating it again raises CollectionInvalid.
        db = self.db
        yield db.drop_collection('test_collection2')
        collection = yield db.create_collection('test_collection2')
        self.assertTrue(isinstance(collection, motor.MotorCollection))
        self.assertTrue(
            'test_collection2' in (yield db.collection_names()))

        with self.assertRaises(CollectionInvalid):
            yield db.create_collection('test_collection2')

        yield db.drop_collection('test_collection2')

        # Test creating capped collection
        collection = yield db.create_collection(
            'test_capped', capped=True, size=4096)

        self.assertTrue(isinstance(collection, motor.MotorCollection))
        self.assertEqual(
            {"capped": True, 'size': 4096},
            (yield db.test_capped.options()))
        yield db.drop_collection('test_capped')

    @gen_test
    def test_drop_collection(self):
        # Make sure we can pass a MotorCollection instance to drop_collection
        db = self.db
        collection = db.test_drop_collection
        yield collection.insert_one({})
        names = yield db.collection_names()
        self.assertTrue('test_drop_collection' in names)
        yield db.drop_collection(collection)
        names = yield db.collection_names()
        self.assertFalse('test_drop_collection' in names)

    @ignore_deprecations
    @gen_test
    def test_auto_ref_and_deref(self):
        # Test same functionality as in PyMongo's test_database.py; the
        # implementation for Motor for async is a little complex so we test
        # that it works here, and we don't just rely on synchrotest
        # to cover it.
        db = self.db

        # We test a special hack where add_son_manipulator corrects our mistake
        # if we pass a MotorDatabase, instead of Database, to AutoReference.
        db.add_son_manipulator(AutoReference(db))
        db.add_son_manipulator(NamespaceInjector())

        a = {"hello": "world"}
        b = {"test": a}
        c = {"another test": b}

        yield db.a.delete_many({})
        yield db.b.delete_many({})
        yield db.c.delete_many({})
        yield db.a.save(a)
        yield db.b.save(b)
        yield db.c.save(c)
        a["hello"] = "mike"
        yield db.a.save(a)
        result_a = yield db.a.find_one()
        result_b = yield db.b.find_one()
        result_c = yield db.c.find_one()

        self.assertEqual(a, result_a)
        self.assertEqual(a, result_b["test"])
        self.assertEqual(a, result_c["another test"]["test"])
        self.assertEqual(b, result_b)
        self.assertEqual(b, result_c["another test"])
        self.assertEqual(c, result_c)

    # SCRAM-SHA-1 is slow, install backports.pbkdf2 for speed.
    @gen_test(timeout=30)
    def test_authenticate(self):
        # self.db is logged in as root.
        with ignore_deprecations():
            yield self.db.add_user("mike", "password")

        client = motor.MotorClient(env.host, env.port,
                                   **self.get_client_kwargs())
        db = client.motor_test
        try:
            # Authenticate many times at once to test concurrency.
            yield [db.authenticate("mike", "password") for _ in range(10)]

            # Just make sure there are no exceptions here.
            yield db.remove_user("mike")
            yield db.logout()
            info = yield self.db.command("usersInfo", "mike")
            users = info.get('users', [])
            self.assertFalse("mike" in [u['user'] for u in users])

        finally:
            yield remove_all_users(self.db)
            test.env.sync_cx.close()

    @gen_test
    def test_validate_collection(self):
        db = self.db

        with self.assertRaises(TypeError):
            yield db.validate_collection(5)
        with self.assertRaises(TypeError):
            yield db.validate_collection(None)
        with self.assertRaises(OperationFailure):
            yield db.validate_collection("test.doesnotexist")
        with self.assertRaises(OperationFailure):
            yield db.validate_collection(db.test.doesnotexist)

        yield db.test.insert_one({"dummy": "object"})
        self.assertTrue((yield db.validate_collection("test")))
        self.assertTrue((yield db.validate_collection(db.test)))

    def test_get_collection(self):
        codec_options = CodecOptions(
            tz_aware=True, uuid_representation=JAVA_LEGACY)
        write_concern = WriteConcern(w=2, j=True)
        coll = self.db.get_collection(
            'foo', codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(coll, motor.MotorCollection))
        self.assertEqual('foo', coll.name)
        self.assertEqual(codec_options, coll.codec_options)
        self.assertEqual(ReadPreference.SECONDARY, coll.read_preference)
        self.assertEqual(write_concern, coll.write_concern)

        pref = Secondary([{"dc": "sf"}])
        coll = self.db.get_collection('foo', read_preference=pref)
        self.assertEqual(pref, coll.read_preference)
        self.assertEqual(self.db.codec_options, coll.codec_options)
        self.assertEqual(self.db.write_concern, coll.write_concern)


if __name__ == '__main__':
    unittest.main()
