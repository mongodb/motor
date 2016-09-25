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

"""Test Motor's bulk API with asyncio."""

import unittest

from pymongo.errors import BulkWriteError

from motor.motor_asyncio import AsyncIOMotorBulkOperationBuilder
from test.asyncio_tests import asyncio_test, AsyncIOTestCase


class TestAsyncIOBulk(AsyncIOTestCase):

    # Little testing is needed: Most of the logic is in PyMongo, and Motor's
    # bulk operations are lightly tested with Tornado already.

    @asyncio_test(timeout=30)
    def test_multiple_error_ordered_batch(self):
        yield from self.collection.delete_many({})
        yield from self.collection.create_index('a', unique=True)
        try:
            bulk = self.collection.initialize_ordered_bulk_op()
            self.assertTrue(isinstance(bulk,
                                       AsyncIOMotorBulkOperationBuilder))

            bulk.insert({'b': 1, 'a': 1})
            bulk.find({'b': 2}).upsert().update_one({'$set': {'a': 1}})
            bulk.find({'b': 3}).upsert().update_one({'$set': {'a': 2}})
            bulk.find({'b': 2}).upsert().update_one({'$set': {'a': 1}})
            bulk.insert({'b': 4, 'a': 3})
            bulk.insert({'b': 5, 'a': 1})

            try:
                yield from bulk.execute()
            except BulkWriteError as exc:
                result = exc.details
                self.assertEqual(exc.code, 65)
            else:
                self.fail("Error not raised")

            self.assertEqual(1, result['nInserted'])
            self.assertEqual(1, len(result['writeErrors']))

            cursor = self.collection.find({}, {'_id': False})
            docs = yield from cursor.to_list(None)
            self.assertEqual([{'a': 1, 'b': 1}], docs)
        finally:
            yield from self.collection.drop()

    @asyncio_test
    def test_single_unordered_batch(self):
        yield from self.collection.delete_many({})

        bulk = self.collection.initialize_unordered_bulk_op()
        self.assertTrue(isinstance(bulk,
                                   AsyncIOMotorBulkOperationBuilder))

        bulk.insert({'a': 1})
        bulk.find({'a': 1}).update_one({'$set': {'b': 1}})
        bulk.find({'a': 2}).upsert().update_one({'$set': {'b': 2}})
        bulk.insert({'a': 3})
        bulk.find({'a': 3}).remove()
        result = yield from bulk.execute()
        self.assertEqual(0, len(result['writeErrors']))
        upserts = result['upserted']
        self.assertEqual(1, len(upserts))
        self.assertEqual(2, upserts[0]['index'])
        self.assertTrue(upserts[0].get('_id'))

        a_values = yield from self.collection.distinct('a')
        self.assertEqual(
            set([1, 2]),
            set(a_values))


if __name__ == '__main__':
    unittest.main()
