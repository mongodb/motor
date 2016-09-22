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

from motor.motor_asyncio import AsyncIOMotorGridFS
import test
from test import SkipTest
from test.asyncio_tests import asyncio_test, AsyncIOTestCase, at_least
from test.utils import ignore_deprecations


class TestAsyncIOAwait(AsyncIOTestCase):
    @asyncio_test
    async def test_open_client(self):
        client = self.asyncio_client()

        with ignore_deprecations():
            self.assertEqual(client, await client.open())

        client.close()

    @asyncio_test
    async def test_open_client_rs(self):
        if not test.env.is_replica_set:
            raise SkipTest("Not connected to a replica set")

        rsc = self.asyncio_rsc()

        with ignore_deprecations():
            self.assertEqual(rsc, await rsc.open())

    @asyncio_test
    async def test_to_list(self):
        collection = self.collection
        await collection.remove()

        results = await collection.find().sort('_id').to_list(length=None)
        self.assertEqual([], results)

        docs = [{'_id': 1}, {'_id': 2}]
        await collection.insert(docs)
        cursor = collection.find().sort('_id')
        results = await cursor.to_list(length=None)
        self.assertEqual(docs, results)
        results = await cursor.to_list(length=None)
        self.assertEqual([], results)

    @asyncio_test
    async def test_iter_cursor(self):
        collection = self.collection
        await collection.remove()

        for n_docs in 0, 1, 2, 10:
            if n_docs:
                docs = [{'_id': i} for i in range(n_docs)]
                await collection.insert(docs)

            # Force extra batches to test iteration.
            j = 0
            async for doc in collection.find().sort('_id').batch_size(3):
                self.assertEqual(j, doc['_id'])
                j += 1

            self.assertEqual(j, n_docs)

            await collection.remove()

    @asyncio_test
    async def test_iter_aggregate(self):
        if not (await at_least(self.cx, (2, 5, 1))):
            raise SkipTest("Aggregation cursor requires MongoDB >= 2.5.1")

        collection = self.collection
        await collection.remove()
        pipeline = [{'$sort': {'_id': 1}}]

        # Empty iterator.
        async for _ in collection.aggregate(pipeline):
            self.fail()

        for n_docs in 1, 2, 10:
            if n_docs:
                docs = [{'_id': i} for i in range(n_docs)]
                await collection.insert(docs)

            # Force extra batches to test iteration.
            j = 0
            async for doc in collection.aggregate(pipeline,
                                                  cursor={'batchSize': 3}):
                self.assertEqual(j, doc['_id'])
                j += 1

            self.assertEqual(j, n_docs)

            await collection.remove()

    @asyncio_test
    async def test_iter_gridfs(self):
        gfs = AsyncIOMotorGridFS(self.db)

        async def cleanup():
            await self.db.fs.files.remove()
            await self.db.fs.chunks.remove()

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
