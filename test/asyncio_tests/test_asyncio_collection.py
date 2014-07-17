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

"""Test AsyncIOMotorCollection."""

import asyncio
import unittest
from unittest import SkipTest
from pymongo import ReadPreference

from pymongo.errors import DuplicateKeyError

from motor.motor_asyncio import AsyncIOMotorCollection, \
    AsyncIOMotorCommandCursor
import test
from test.asyncio_tests import asyncio_test, AsyncIOTestCase, version, \
    skip_if_mongos, at_least


class TestAsyncIOCollection(AsyncIOTestCase):
    @asyncio_test
    def test_collection(self):
        # Test that we can create a collection directly, not just from
        # database accessors.
        collection = AsyncIOMotorCollection(self.db, 'test_collection')

        # Make sure we got the right collection and it can do an operation
        self.assertEqual('test_collection', collection.name)
        yield from collection.remove()
        yield from collection.insert({'_id': 1})
        doc = yield from collection.find_one({'_id': 1})
        self.assertEqual(1, doc['_id'])

        # If you pass kwargs to PyMongo's Collection(), it calls
        # db.create_collection(). Motor can't do I/O in a constructor
        # so this is prohibited.
        self.assertRaises(
            TypeError,
            AsyncIOMotorCollection,
            self.db,
            'test_collection',
            capped=True)

    @asyncio_test
    def test_save_with_id(self):
        # save() returns the _id, in this case 5.
        self.assertEqual(
            5,
            (yield from self.collection.save({'_id': 5})))

    @asyncio_test
    def test_unacknowledged_insert(self):
        # Insert id 1 without a callback or w=1.
        coll = self.db.test_unacknowledged_insert
        coll.insert({'_id': 1})

        # The insert is eventually executed.
        while not (yield from coll.count()):
            yield from asyncio.sleep(0.1, loop=self.loop)

        # DuplicateKeyError not raised.
        future = coll.insert({'_id': 1})
        yield from coll.insert({'_id': 1}, w=0)

        with self.assertRaises(DuplicateKeyError):
            yield from future

    @asyncio_test
    def test_aggregation_cursor(self):
        if not (yield from at_least(self.cx, (2, 5, 1))):
            raise SkipTest("Aggregation cursor requires MongoDB >= 2.5.1")

        db = self.db

        # A small collection which returns only an initial batch,
        # and a larger one that requires a getMore.
        for collection_size in (10, 1000):
            yield from db.drop_collection("test")
            yield from db.test.insert([{'_id': i} for i in range(collection_size)])
            expected_sum = sum(range(collection_size))
            cursor = yield from db.test.aggregate(
                {'$project': {'_id': '$_id'}}, cursor={})

            docs = yield from cursor.to_list(collection_size)
            self.assertEqual(
                expected_sum,
                sum(doc['_id'] for doc in docs))

    @asyncio_test(timeout=30)
    def test_parallel_scan(self):
        if not (yield from at_least(self.cx, (2, 5, 5))):
            raise SkipTest("Requires MongoDB >= 2.5.5")

        yield from skip_if_mongos(self.cx)

        collection = self.collection

        # Enough documents that each cursor requires multiple batches.
        yield from collection.remove()
        yield from collection.insert(({'_id': i} for i in range(8000)), w=test.env.w)
        if test.env.is_replica_set:
            client = self.asyncio_rsc()

            # Test that getMore messages are sent to the right server.
            client.read_preference = ReadPreference.SECONDARY
            collection = client.motor_test.test_collection

        docs = []

        @asyncio.coroutine
        def f(cursor):
            self.assertTrue(isinstance(cursor, AsyncIOMotorCommandCursor))

            while (yield from cursor.fetch_next):
                docs.append(cursor.next_object())

        cursors = yield from collection.parallel_scan(3)
        yield from asyncio.wait(
            [f(cursor) for cursor in cursors],
            loop=self.loop)

        self.assertEqual(len(docs), (yield from collection.count()))


if __name__ == '__main__':
    unittest.main()
