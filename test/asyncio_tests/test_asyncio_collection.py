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

"""Test AsyncIOMotorCollection."""

import asyncio
import sys
import traceback
import unittest
from test.asyncio_tests import AsyncIOTestCase, asyncio_test
from test.utils import ignore_deprecations

from bson import CodecOptions
from bson.binary import JAVA_LEGACY
from pymongo import ReadPreference, WriteConcern
from pymongo.errors import BulkWriteError, DuplicateKeyError, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import Secondary

from motor.motor_asyncio import AsyncIOMotorCollection


class TestAsyncIOCollection(AsyncIOTestCase):
    @asyncio_test
    async def test_collection(self):
        # Test that we can create a collection directly, not just from
        # database accessors.
        collection = AsyncIOMotorCollection(self.db, "test_collection")

        # Make sure we got the right collection and it can do an operation
        self.assertEqual("test_collection", collection.name)
        await collection.delete_many({})
        await collection.insert_one({"_id": 1})
        doc = await collection.find_one({"_id": 1})
        self.assertEqual(1, doc["_id"])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError, AsyncIOMotorCollection, self.db, "test_collection", capped=True
        )

    @asyncio_test
    async def test_dotted_collection_name(self):
        # Ensure that remove, insert, and find work on collections with dots
        # in their names.
        for coll in (self.db.foo.bar, self.db.foo.bar.baz):
            await coll.delete_many({})
            result = await coll.insert_one({"_id": "xyzzy"})
            self.assertEqual("xyzzy", result.inserted_id)
            result = await coll.find_one({"_id": "xyzzy"})
            self.assertEqual(result["_id"], "xyzzy")
            await coll.delete_many({})
            resp = await coll.find_one({"_id": "xyzzy"})
            self.assertEqual(None, resp)

    def test_call(self):
        # Prevents user error with nice message.
        try:
            self.db.foo()
        except TypeError as e:
            self.assertTrue("no such method exists" in str(e))
        else:
            self.fail("Expected TypeError")

    @ignore_deprecations
    @asyncio_test
    async def test_update(self):
        await self.collection.insert_one({"_id": 1})
        result = await self.collection.update_one({"_id": 1}, {"$set": {"foo": "bar"}})

        self.assertIsNone(result.upserted_id)
        self.assertEqual(1, result.modified_count)

    @ignore_deprecations
    @asyncio_test
    async def test_update_bad(self):
        # Violate a unique index, make sure we handle error well
        coll = self.db.unique_collection
        await coll.create_index("s", unique=True)

        try:
            await coll.insert_many([{"s": 1}, {"s": 2}])
            with self.assertRaises(DuplicateKeyError):
                await coll.update_one({"s": 2}, {"$set": {"s": 1}})

        finally:
            await coll.drop()

    @asyncio_test
    async def test_insert_one(self):
        collection = self.collection
        result = await collection.insert_one({"_id": 201})
        self.assertEqual(201, result.inserted_id)

    @ignore_deprecations
    @asyncio_test
    async def test_insert_many_one_bad(self):
        collection = self.collection
        await collection.insert_one({"_id": 2})

        # Violate a unique index in one of many updates, handle error.
        with self.assertRaises(BulkWriteError):
            await collection.insert_many([{"_id": 1}, {"_id": 2}, {"_id": 3}])  # Already exists

        # First insert should have succeeded, but not second or third.
        self.assertEqual(set([1, 2]), set((await collection.distinct("_id"))))

    @asyncio_test
    async def test_delete_one(self):
        # Remove a document twice, check that we get a success responses
        # and n = 0 for the second time.
        await self.collection.insert_one({"_id": 1})
        result = await self.collection.delete_one({"_id": 1})

        # First time we remove, n = 1
        self.assertEqual(1, result.raw_result["n"])
        self.assertEqual(1, result.raw_result["ok"])
        self.assertEqual(None, result.raw_result.get("err"))

        result = await self.collection.delete_one({"_id": 1})

        # Second time, document is already gone, n = 0
        self.assertEqual(0, result.raw_result["n"])
        self.assertEqual(1, result.raw_result["ok"])
        self.assertEqual(None, result.raw_result.get("err"))

    @ignore_deprecations
    @asyncio_test
    async def test_unacknowledged_insert(self):
        coll = self.db.test_unacknowledged_insert
        await coll.with_options(write_concern=WriteConcern(0)).insert_one({"_id": 1})

        # The insert is eventually executed.
        while not (await coll.count_documents({})):
            await asyncio.sleep(0.1)

    @ignore_deprecations
    @asyncio_test
    async def test_unacknowledged_update(self):
        coll = self.collection

        await coll.insert_one({"_id": 1})
        await coll.with_options(write_concern=WriteConcern(0)).update_one(
            {"_id": 1}, {"$set": {"a": 1}}
        )

        while not (await coll.find_one({"a": 1})):
            await asyncio.sleep(0.1)

    @ignore_deprecations
    @asyncio_test
    async def test_indexes(self):
        test_collection = self.collection

        # Create an index
        idx_name = await test_collection.create_index([("foo", 1)])
        index_info = await test_collection.index_information()
        self.assertEqual([("foo", 1)], index_info[idx_name]["key"])

        # Don't test drop_index or drop_indexes -- Synchro tests them

    async def _make_test_data(self, n):
        await self.db.drop_collection("test")
        await self.db.test.insert_many([{"_id": i} for i in range(n)])
        expected_sum = sum(range(n))
        return expected_sum

    pipeline = [{"$project": {"_id": "$_id"}}]

    @asyncio_test(timeout=30)
    async def test_aggregation_cursor(self):
        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            expected_sum = await self._make_test_data(collection_size)
            cursor = db.test.aggregate(self.pipeline)
            docs = await cursor.to_list(collection_size)
            self.assertEqual(expected_sum, sum(doc["_id"] for doc in docs))

    @asyncio_test
    async def test_aggregation_cursor_exc_info(self):
        await self._make_test_data(200)
        cursor = self.db.test.aggregate(self.pipeline)
        await cursor.to_list(length=10)
        await self.db.test.drop()
        try:
            await cursor.to_list(length=None)
        except OperationFailure:
            _, _, tb = sys.exc_info()

            # The call tree should include PyMongo code we ran on a thread.
            formatted = "\n".join(traceback.format_tb(tb))
            self.assertTrue(
                "_unpack_response" in formatted or "_check_command_response" in formatted
            )

    @asyncio_test
    async def test_aggregate_cursor_del(self):
        cursor = self.db.test.aggregate(self.pipeline)
        del cursor
        cursor = self.db.test.aggregate(self.pipeline)
        await cursor.close()
        del cursor

    def test_with_options(self):
        coll = self.db.test
        codec_options = CodecOptions(tz_aware=True, uuid_representation=JAVA_LEGACY)

        write_concern = WriteConcern(w=2, j=True)
        coll2 = coll.with_options(codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(coll2, AsyncIOMotorCollection))
        self.assertEqual(codec_options, coll2.codec_options)
        self.assertEqual(Secondary(), coll2.read_preference)
        self.assertEqual(write_concern, coll2.write_concern)

        pref = Secondary([{"dc": "sf"}])
        coll2 = coll.with_options(read_preference=pref)
        self.assertEqual(pref, coll2.read_preference)
        self.assertEqual(coll.codec_options, coll2.codec_options)
        self.assertEqual(coll.write_concern, coll2.write_concern)

    def test_sub_collection(self):
        # Verify that a collection with a dotted name inherits options from its
        # parent collection.
        write_concern = WriteConcern(w=2, j=True)
        read_concern = ReadConcern("majority")
        read_preference = Secondary([{"dc": "sf"}])
        codec_options = CodecOptions(tz_aware=True, uuid_representation=JAVA_LEGACY)

        coll1 = self.db.get_collection(
            "test",
            write_concern=write_concern,
            read_concern=read_concern,
            read_preference=read_preference,
            codec_options=codec_options,
        )

        coll2 = coll1.subcollection
        coll3 = coll1["subcollection"]

        for c in [coll1, coll2, coll3]:
            self.assertEqual(write_concern, c.write_concern)
            self.assertEqual(read_concern, c.read_concern)
            self.assertEqual(read_preference, c.read_preference)
            self.assertEqual(codec_options, c.codec_options)


if __name__ == "__main__":
    unittest.main()
