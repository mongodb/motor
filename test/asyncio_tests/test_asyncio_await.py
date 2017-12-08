# Copyright 2015 MongoDB, Inc.
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

from __future__ import unicode_literals, absolute_import

import warnings

from motor.motor_asyncio import AsyncIOMotorGridFS
import test
from test.asyncio_tests import asyncio_test, AsyncIOTestCase


class TestAsyncIOAwait(AsyncIOTestCase):
    @asyncio_test
    async def test_to_list(self):
        collection = self.collection
        await collection.delete_many({})

        results = await collection.find().sort('_id').to_list(length=None)
        self.assertEqual([], results)

        docs = [{'_id': 1}, {'_id': 2}]
        await collection.insert_many(docs)
        cursor = collection.find().sort('_id')
        results = await cursor.to_list(length=None)
        self.assertEqual(docs, results)
        results = await cursor.to_list(length=None)
        self.assertEqual([], results)

    @asyncio_test
    async def test_iter_cursor(self):
        collection = self.collection
        await collection.delete_many({})

        for n_docs in 0, 1, 2, 10:
            if n_docs:
                docs = [{'_id': i} for i in range(n_docs)]
                await collection.insert_many(docs)

            # Force extra batches to test iteration.
            j = 0
            async for doc in collection.find().sort('_id').batch_size(3):
                self.assertEqual(j, doc['_id'])
                j += 1

            self.assertEqual(j, n_docs)

            await collection.delete_many({})

    @asyncio_test
    async def test_iter_aggregate(self):
        collection = self.collection
        await collection.delete_many({})
        pipeline = [{'$sort': {'_id': 1}}]

        # Empty iterator.
        async for _ in collection.aggregate(pipeline):
            self.fail()

        for n_docs in 1, 2, 10:
            if n_docs:
                docs = [{'_id': i} for i in range(n_docs)]
                await collection.insert_many(docs)

            # Force extra batches to test iteration.
            j = 0
            async for doc in collection.aggregate(pipeline,
                                                  cursor={'batchSize': 3}):
                self.assertEqual(j, doc['_id'])
                j += 1

            self.assertEqual(j, n_docs)

            await collection.delete_many({})

    @asyncio_test
    async def test_iter_gridfs(self):
        gfs = AsyncIOMotorGridFS(self.db)

        async def cleanup():
            await self.db.fs.files.delete_many({})
            await self.db.fs.chunks.delete_many({})

        await cleanup()

        # Empty iterator.
        async for _ in gfs.find({'_id': 1}):
            self.fail()

        data = b'data'

        for n_files in 1, 2, 10:
            for i in range(n_files):
                await gfs.put(data, filename='filename')

            # Force extra batches to test iteration.
            j = 0
            async for _ in gfs.find({'filename': 'filename'}).batch_size(3):
                j += 1

            self.assertEqual(j, n_files)
            await cleanup()

        async with await gfs.new_file(_id=1, chunk_size=1) as f:
            await f.write(data)

        gout = await gfs.find_one({'_id': 1})
        chunks = []
        async for chunk in gout:
            chunks.append(chunk)

        self.assertEqual(len(chunks), len(data))
        self.assertEqual(b''.join(chunks), data)

    @asyncio_test
    async def test_stream_to_handler(self):
        # Sort of Tornado-specific, but it does work with asyncio.
        fs = AsyncIOMotorGridFS(self.db)
        content_length = 1000
        await fs.delete(1)
        self.assertEqual(1, await fs.put(b'a' * content_length, _id=1))
        gridout = await fs.get(1)
        handler = test.MockRequestHandler()
        await gridout.stream_to_handler(handler)
        self.assertEqual(content_length, handler.n_written)
        await fs.delete(1)

    @asyncio_test
    async def test_cursor_iter(self):
        # Have we handled the async iterator change in Python 3.5.2?:
        # python.org/dev/peps/pep-0492/#api-design-and-implementation-revisions
        with warnings.catch_warnings(record=True) as w:
            async for _ in self.collection.find():
                pass

        if w:
            self.fail(w[0].message)

    @asyncio_test
    async def test_list_indexes(self):
        await self.collection.drop()
        await self.collection.create_index([('x', 1)])
        await self.collection.create_index([('y', -1)])
        keys = set()
        async for info in self.collection.list_indexes():
            keys.add(info['name'])

        self.assertEqual(keys, {'_id_', 'x_1', 'y_-1'})
