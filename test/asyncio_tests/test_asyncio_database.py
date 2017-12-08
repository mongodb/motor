# Copyright 2014 MongoDB, Inc.
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

"""Test AsyncIOMotorDatabase."""

import asyncio
import unittest
from unittest import SkipTest

import pymongo.database
from bson import CodecOptions
from bson.binary import JAVA_LEGACY
from pymongo import ReadPreference, WriteConcern
from pymongo.errors import CollectionInvalid, OperationFailure
from pymongo.read_preferences import Secondary
from pymongo.son_manipulator import NamespaceInjector, AutoReference

from motor.motor_asyncio import (AsyncIOMotorDatabase,
                                 AsyncIOMotorClient,
                                 AsyncIOMotorCollection)
import test
from test import env
from test.asyncio_tests import (asyncio_test,
                                AsyncIOTestCase,
                                remove_all_users)
from test.utils import ignore_deprecations


class TestAsyncIODatabase(AsyncIOTestCase):
    @asyncio_test
    def test_database(self):
        # Test that we can create a db directly, not just get on from
        # AsyncIOMotorClient.
        db = AsyncIOMotorDatabase(self.cx, 'motor_test')

        # Make sure we got the right DB and it can do an operation.
        self.assertEqual('motor_test', db.name)
        yield from db.test_collection.delete_many({})
        yield from db.test_collection.insert_one({'_id': 1})
        doc = yield from db.test_collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

    def test_collection_named_delegate(self):
        db = self.db
        self.assertTrue(isinstance(db.delegate, pymongo.database.Database))
        self.assertTrue(isinstance(db['delegate'], AsyncIOMotorCollection))
        db.client.close()

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.cx.foo()
        except TypeError as e:
            self.assertTrue('no such method exists' in str(e))
        else:
            self.fail('Expected TypeError')

    @asyncio_test
    def test_command(self):
        result = yield from self.cx.admin.command("buildinfo")
        # Make sure we got some sane result or other.
        self.assertEqual(1, result['ok'])

    @asyncio_test
    def test_create_collection(self):
        # Test creating collection, return val is wrapped in
        # AsyncIOMotorCollection, creating it again raises CollectionInvalid.
        db = self.db
        yield from db.drop_collection('test_collection2')
        collection = yield from db.create_collection('test_collection2')
        self.assertTrue(isinstance(collection, AsyncIOMotorCollection))
        self.assertTrue(
            'test_collection2' in (yield from db.collection_names()))

        with self.assertRaises(CollectionInvalid):
            yield from db.create_collection('test_collection2')

    @asyncio_test
    def test_drop_collection(self):
        # Make sure we can pass an AsyncIOMotorCollection instance to
        # drop_collection.
        db = self.db
        collection = db.test_drop_collection
        yield from collection.insert_one({})
        names = yield from db.collection_names()
        self.assertTrue('test_drop_collection' in names)
        yield from db.drop_collection(collection)
        names = yield from db.collection_names()
        self.assertFalse('test_drop_collection' in names)

    @ignore_deprecations
    @asyncio_test
    def test_auto_ref_and_deref(self):
        # Test same functionality as in PyMongo's test_database.py; the
        # implementation for Motor for async is a little complex so we test
        # that it works here, and we don't just rely on synchrotest
        # to cover it.
        db = self.db

        # We test a special hack where add_son_manipulator corrects our mistake
        # if we pass an AsyncIOMotorDatabase, instead of Database, to
        # AutoReference.
        db.add_son_manipulator(AutoReference(db))
        db.add_son_manipulator(NamespaceInjector())

        a = {"hello": "world"}
        b = {"test": a}
        c = {"another test": b}

        yield from db.a.delete_many({})
        yield from db.b.delete_many({})
        yield from db.c.delete_many({})
        yield from db.a.save(a)
        yield from db.b.save(b)
        yield from db.c.save(c)
        a["hello"] = "jesse"
        yield from db.a.save(a)
        result_a = yield from db.a.find_one()
        result_b = yield from db.b.find_one()
        result_c = yield from db.c.find_one()

        self.assertEqual(a, result_a)
        self.assertEqual(a, result_b["test"])
        self.assertEqual(a, result_c["another test"]["test"])
        self.assertEqual(b, result_b)
        self.assertEqual(b, result_c["another test"])
        self.assertEqual(c, result_c)

    @asyncio_test
    def test_authenticate(self):
        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # self.db is logged in as root.
        yield from self.db.add_user("jesse", "password")
        db = AsyncIOMotorClient(env.host, env.port,
                                **self.get_client_kwargs()).motor_test
        try:
            # Authenticate many times at once to test concurrency.
            yield from asyncio.wait(
                [db.authenticate("jesse", "password") for _ in range(10)],
                loop=self.loop)

            # Just make sure there are no exceptions here.
            yield from db.remove_user("jesse")
            yield from db.logout()
            info = yield from self.db.command("usersInfo", "jesse")
            users = info.get('users', [])
            self.assertFalse("jesse" in [u['user'] for u in users])

        finally:
            yield from remove_all_users(self.db)
            test.env.sync_cx.close()

    @asyncio_test
    def test_validate_collection(self):
        db = self.db

        with self.assertRaises(TypeError):
            yield from db.validate_collection(5)
        with self.assertRaises(TypeError):
            yield from db.validate_collection(None)
        with self.assertRaises(OperationFailure):
            yield from db.validate_collection("test.doesnotexist")
        with self.assertRaises(OperationFailure):
            yield from db.validate_collection(db.test.doesnotexist)

        yield from db.test.insert_one({"dummy": "object"})
        self.assertTrue((yield from db.validate_collection("test")))
        self.assertTrue((yield from db.validate_collection(db.test)))

    def test_get_collection(self):
        codec_options = CodecOptions(
            tz_aware=True, uuid_representation=JAVA_LEGACY)
        write_concern = WriteConcern(w=2, j=True)
        coll = self.db.get_collection(
            'foo', codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(coll, AsyncIOMotorCollection))
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
