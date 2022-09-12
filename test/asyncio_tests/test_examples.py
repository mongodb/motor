# Copyright 2018-present MongoDB, Inc.
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

"""MongoDB documentation examples with Motor and asyncio."""

import asyncio
import base64
import datetime
import unittest
from io import StringIO
from test import env
from test.asyncio_tests import AsyncIOTestCase, asyncio_test
from test.utils import wait_until
from unittest.mock import patch

import pymongo
from bson import Binary
from bson.codec_options import CodecOptions
from pymongo import WriteConcern
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.read_preferences import ReadPreference
from pymongo.server_api import ServerApi

from motor.motor_asyncio import AsyncIOMotorClientEncryption


async def count(cursor):
    i = 0
    async for _ in cursor:
        i += 1

    return i


class TestExamples(AsyncIOTestCase):
    @classmethod
    def setUpClass(cls):
        env.sync_cx.motor_test.inventory.drop()

    def tearDown(self):
        env.sync_cx.motor_test.inventory.drop()

    @asyncio_test
    async def test_first_three_examples(self):
        db = self.db

        # Start Example 1
        await db.inventory.insert_one(
            {
                "item": "canvas",
                "qty": 100,
                "tags": ["cotton"],
                "size": {"h": 28, "w": 35.5, "uom": "cm"},
            }
        )
        # End Example 1

        self.assertEqual(await db.inventory.count_documents({}), 1)

        # Start Example 2
        cursor = db.inventory.find({"item": "canvas"})
        # End Example 2

        self.assertEqual(await count(cursor), 1)

        # Start Example 3
        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "qty": 25,
                    "tags": ["blank", "red"],
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                },
                {
                    "item": "mat",
                    "qty": 85,
                    "tags": ["gray"],
                    "size": {"h": 27.9, "w": 35.5, "uom": "cm"},
                },
                {
                    "item": "mousepad",
                    "qty": 25,
                    "tags": ["gel", "blue"],
                    "size": {"h": 19, "w": 22.85, "uom": "cm"},
                },
            ]
        )
        # End Example 3

        self.assertEqual(await db.inventory.count_documents({}), 4)

    @asyncio_test
    async def test_query_top_level_fields(self):
        db = self.db

        # Start Example 6
        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "qty": 25,
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "notebook",
                    "qty": 50,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "A",
                },
                {
                    "item": "paper",
                    "qty": 100,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "D",
                },
                {
                    "item": "planner",
                    "qty": 75,
                    "size": {"h": 22.85, "w": 30, "uom": "cm"},
                    "status": "D",
                },
                {
                    "item": "postcard",
                    "qty": 45,
                    "size": {"h": 10, "w": 15.25, "uom": "cm"},
                    "status": "A",
                },
            ]
        )
        # End Example 6

        self.assertEqual(await db.inventory.count_documents({}), 5)

        # Start Example 7
        cursor = db.inventory.find({})
        # End Example 7

        self.assertEqual(await count(cursor), 5)

        # Start Example 9
        cursor = db.inventory.find({"status": "D"})
        # End Example 9

        self.assertEqual(await count(cursor), 2)

        # Start Example 10
        cursor = db.inventory.find({"status": {"$in": ["A", "D"]}})
        # End Example 10

        self.assertEqual(await count(cursor), 5)

        # Start Example 11
        cursor = db.inventory.find({"status": "A", "qty": {"$lt": 30}})
        # End Example 11

        self.assertEqual(await count(cursor), 1)

        # Start Example 12
        cursor = db.inventory.find({"$or": [{"status": "A"}, {"qty": {"$lt": 30}}]})
        # End Example 12

        self.assertEqual(await count(cursor), 3)

        # Start Example 13
        cursor = db.inventory.find(
            {"status": "A", "$or": [{"qty": {"$lt": 30}}, {"item": {"$regex": "^p"}}]}
        )
        # End Example 13

        self.assertEqual(await count(cursor), 2)

    @asyncio_test
    async def test_query_embedded_documents(self):
        db = self.db

        # Start Example 14
        # Subdocument key order matters in a few of these examples so we have
        # to use bson.son.SON instead of a Python dict.
        from bson.son import SON

        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "qty": 25,
                    "size": SON([("h", 14), ("w", 21), ("uom", "cm")]),
                    "status": "A",
                },
                {
                    "item": "notebook",
                    "qty": 50,
                    "size": SON([("h", 8.5), ("w", 11), ("uom", "in")]),
                    "status": "A",
                },
                {
                    "item": "paper",
                    "qty": 100,
                    "size": SON([("h", 8.5), ("w", 11), ("uom", "in")]),
                    "status": "D",
                },
                {
                    "item": "planner",
                    "qty": 75,
                    "size": SON([("h", 22.85), ("w", 30), ("uom", "cm")]),
                    "status": "D",
                },
                {
                    "item": "postcard",
                    "qty": 45,
                    "size": SON([("h", 10), ("w", 15.25), ("uom", "cm")]),
                    "status": "A",
                },
            ]
        )
        # End Example 14

        # Start Example 15
        cursor = db.inventory.find({"size": SON([("h", 14), ("w", 21), ("uom", "cm")])})
        # End Example 15

        self.assertEqual(await count(cursor), 1)

        # Start Example 16
        cursor = db.inventory.find({"size": SON([("w", 21), ("h", 14), ("uom", "cm")])})
        # End Example 16

        self.assertEqual(await count(cursor), 0)

        # Start Example 17
        cursor = db.inventory.find({"size.uom": "in"})
        # End Example 17

        self.assertEqual(await count(cursor), 2)

        # Start Example 18
        cursor = db.inventory.find({"size.h": {"$lt": 15}})
        # End Example 18

        self.assertEqual(await count(cursor), 4)

        # Start Example 19
        cursor = db.inventory.find({"size.h": {"$lt": 15}, "size.uom": "in", "status": "D"})
        # End Example 19

        self.assertEqual(await count(cursor), 1)

    @asyncio_test
    async def test_query_arrays(self):
        db = self.db

        # Start Example 20
        await db.inventory.insert_many(
            [
                {"item": "journal", "qty": 25, "tags": ["blank", "red"], "dim_cm": [14, 21]},
                {"item": "notebook", "qty": 50, "tags": ["red", "blank"], "dim_cm": [14, 21]},
                {
                    "item": "paper",
                    "qty": 100,
                    "tags": ["red", "blank", "plain"],
                    "dim_cm": [14, 21],
                },
                {"item": "planner", "qty": 75, "tags": ["blank", "red"], "dim_cm": [22.85, 30]},
                {"item": "postcard", "qty": 45, "tags": ["blue"], "dim_cm": [10, 15.25]},
            ]
        )
        # End Example 20

        # Start Example 21
        cursor = db.inventory.find({"tags": ["red", "blank"]})
        # End Example 21

        self.assertEqual(await count(cursor), 1)

        # Start Example 22
        cursor = db.inventory.find({"tags": {"$all": ["red", "blank"]}})
        # End Example 22

        self.assertEqual(await count(cursor), 4)

        # Start Example 23
        cursor = db.inventory.find({"tags": "red"})
        # End Example 23

        self.assertEqual(await count(cursor), 4)

        # Start Example 24
        cursor = db.inventory.find({"dim_cm": {"$gt": 25}})
        # End Example 24

        self.assertEqual(await count(cursor), 1)

        # Start Example 25
        cursor = db.inventory.find({"dim_cm": {"$gt": 15, "$lt": 20}})
        # End Example 25

        self.assertEqual(await count(cursor), 4)

        # Start Example 26
        cursor = db.inventory.find({"dim_cm": {"$elemMatch": {"$gt": 22, "$lt": 30}}})
        # End Example 26

        self.assertEqual(await count(cursor), 1)

        # Start Example 27
        cursor = db.inventory.find({"dim_cm.1": {"$gt": 25}})
        # End Example 27

        self.assertEqual(await count(cursor), 1)

        # Start Example 28
        cursor = db.inventory.find({"tags": {"$size": 3}})
        # End Example 28

        self.assertEqual(await count(cursor), 1)

    @asyncio_test
    async def test_query_array_of_documents(self):
        db = self.db

        # Start Example 29
        # Subdocument key order matters in a few of these examples so we have
        # to use bson.son.SON instead of a Python dict.
        from bson.son import SON

        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "instock": [
                        SON([("warehouse", "A"), ("qty", 5)]),
                        SON([("warehouse", "C"), ("qty", 15)]),
                    ],
                },
                {"item": "notebook", "instock": [SON([("warehouse", "C"), ("qty", 5)])]},
                {
                    "item": "paper",
                    "instock": [
                        SON([("warehouse", "A"), ("qty", 60)]),
                        SON([("warehouse", "B"), ("qty", 15)]),
                    ],
                },
                {
                    "item": "planner",
                    "instock": [
                        SON([("warehouse", "A"), ("qty", 40)]),
                        SON([("warehouse", "B"), ("qty", 5)]),
                    ],
                },
                {
                    "item": "postcard",
                    "instock": [
                        SON([("warehouse", "B"), ("qty", 15)]),
                        SON([("warehouse", "C"), ("qty", 35)]),
                    ],
                },
            ]
        )
        # End Example 29

        # Start Example 30
        cursor = db.inventory.find({"instock": SON([("warehouse", "A"), ("qty", 5)])})
        # End Example 30

        self.assertEqual(await count(cursor), 1)

        # Start Example 31
        cursor = db.inventory.find({"instock": SON([("qty", 5), ("warehouse", "A")])})
        # End Example 31

        self.assertEqual(await count(cursor), 0)

        # Start Example 32
        cursor = db.inventory.find({"instock.0.qty": {"$lte": 20}})
        # End Example 32

        self.assertEqual(await count(cursor), 3)

        # Start Example 33
        cursor = db.inventory.find({"instock.qty": {"$lte": 20}})
        # End Example 33

        self.assertEqual(await count(cursor), 5)

        # Start Example 34
        cursor = db.inventory.find({"instock": {"$elemMatch": {"qty": 5, "warehouse": "A"}}})
        # End Example 34

        self.assertEqual(await count(cursor), 1)

        # Start Example 35
        cursor = db.inventory.find({"instock": {"$elemMatch": {"qty": {"$gt": 10, "$lte": 20}}}})
        # End Example 35

        self.assertEqual(await count(cursor), 3)

        # Start Example 36
        cursor = db.inventory.find({"instock.qty": {"$gt": 10, "$lte": 20}})
        # End Example 36

        self.assertEqual(await count(cursor), 4)

        # Start Example 37
        cursor = db.inventory.find({"instock.qty": 5, "instock.warehouse": "A"})
        # End Example 37

        self.assertEqual(await count(cursor), 2)

    @asyncio_test
    async def test_query_null(self):
        db = self.db

        # Start Example 38
        await db.inventory.insert_many([{"_id": 1, "item": None}, {"_id": 2}])
        # End Example 38

        # Start Example 39
        cursor = db.inventory.find({"item": None})
        # End Example 39

        self.assertEqual(await count(cursor), 2)

        # Start Example 40
        cursor = db.inventory.find({"item": {"$type": 10}})
        # End Example 40

        self.assertEqual(await count(cursor), 1)

        # Start Example 41
        cursor = db.inventory.find({"item": {"$exists": False}})
        # End Example 41

        self.assertEqual(await count(cursor), 1)

    @asyncio_test
    async def test_projection(self):
        db = self.db

        # Start Example 42
        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "status": "A",
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                    "instock": [{"warehouse": "A", "qty": 5}],
                },
                {
                    "item": "notebook",
                    "status": "A",
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "instock": [{"warehouse": "C", "qty": 5}],
                },
                {
                    "item": "paper",
                    "status": "D",
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "instock": [{"warehouse": "A", "qty": 60}],
                },
                {
                    "item": "planner",
                    "status": "D",
                    "size": {"h": 22.85, "w": 30, "uom": "cm"},
                    "instock": [{"warehouse": "A", "qty": 40}],
                },
                {
                    "item": "postcard",
                    "status": "A",
                    "size": {"h": 10, "w": 15.25, "uom": "cm"},
                    "instock": [{"warehouse": "B", "qty": 15}, {"warehouse": "C", "qty": 35}],
                },
            ]
        )
        # End Example 42

        # Start Example 43
        cursor = db.inventory.find({"status": "A"})
        # End Example 43

        self.assertEqual(await count(cursor), 3)

        # Start Example 44
        cursor = db.inventory.find({"status": "A"}, {"item": 1, "status": 1})
        # End Example 44

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 45
        cursor = db.inventory.find({"status": "A"}, {"item": 1, "status": 1, "_id": 0})
        # End Example 45

        async for doc in cursor:
            self.assertFalse("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 46
        cursor = db.inventory.find({"status": "A"}, {"status": 0, "instock": 0})
        # End Example 46

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertFalse("status" in doc)
            self.assertTrue("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 47
        cursor = db.inventory.find({"status": "A"}, {"item": 1, "status": 1, "size.uom": 1})
        # End Example 47

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertTrue("size" in doc)
            self.assertFalse("instock" in doc)
            size = doc["size"]
            self.assertTrue("uom" in size)
            self.assertFalse("h" in size)
            self.assertFalse("w" in size)

        # Start Example 48
        cursor = db.inventory.find({"status": "A"}, {"size.uom": 0})
        # End Example 48

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertTrue("size" in doc)
            self.assertTrue("instock" in doc)
            size = doc["size"]
            self.assertFalse("uom" in size)
            self.assertTrue("h" in size)
            self.assertTrue("w" in size)

        # Start Example 49
        cursor = db.inventory.find({"status": "A"}, {"item": 1, "status": 1, "instock.qty": 1})
        # End Example 49

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertTrue("instock" in doc)
            for subdoc in doc["instock"]:
                self.assertFalse("warehouse" in subdoc)
                self.assertTrue("qty" in subdoc)

        # Start Example 50
        cursor = db.inventory.find(
            {"status": "A"}, {"item": 1, "status": 1, "instock": {"$slice": -1}}
        )
        # End Example 50

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertTrue("instock" in doc)
            self.assertEqual(len(doc["instock"]), 1)

    @asyncio_test
    async def test_update_and_replace(self):
        db = self.db

        # Start Example 51
        await db.inventory.insert_many(
            [
                {
                    "item": "canvas",
                    "qty": 100,
                    "size": {"h": 28, "w": 35.5, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "journal",
                    "qty": 25,
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "mat",
                    "qty": 85,
                    "size": {"h": 27.9, "w": 35.5, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "mousepad",
                    "qty": 25,
                    "size": {"h": 19, "w": 22.85, "uom": "cm"},
                    "status": "P",
                },
                {
                    "item": "notebook",
                    "qty": 50,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "P",
                },
                {
                    "item": "paper",
                    "qty": 100,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "D",
                },
                {
                    "item": "planner",
                    "qty": 75,
                    "size": {"h": 22.85, "w": 30, "uom": "cm"},
                    "status": "D",
                },
                {
                    "item": "postcard",
                    "qty": 45,
                    "size": {"h": 10, "w": 15.25, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "sketchbook",
                    "qty": 80,
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "sketch pad",
                    "qty": 95,
                    "size": {"h": 22.85, "w": 30.5, "uom": "cm"},
                    "status": "A",
                },
            ]
        )
        # End Example 51

        # Start Example 52
        await db.inventory.update_one(
            {"item": "paper"},
            {"$set": {"size.uom": "cm", "status": "P"}, "$currentDate": {"lastModified": True}},
        )
        # End Example 52

        async for doc in db.inventory.find({"item": "paper"}):
            self.assertEqual(doc["size"]["uom"], "cm")
            self.assertEqual(doc["status"], "P")
            self.assertTrue("lastModified" in doc)

        # Start Example 53
        await db.inventory.update_many(
            {"qty": {"$lt": 50}},
            {"$set": {"size.uom": "in", "status": "P"}, "$currentDate": {"lastModified": True}},
        )
        # End Example 53

        async for doc in db.inventory.find({"qty": {"$lt": 50}}):
            self.assertEqual(doc["size"]["uom"], "in")
            self.assertEqual(doc["status"], "P")
            self.assertTrue("lastModified" in doc)

        # Start Example 54
        await db.inventory.replace_one(
            {"item": "paper"},
            {
                "item": "paper",
                "instock": [{"warehouse": "A", "qty": 60}, {"warehouse": "B", "qty": 40}],
            },
        )
        # End Example 54

        async for doc in db.inventory.find({"item": "paper"}, {"_id": 0}):
            self.assertEqual(len(doc.keys()), 2)
            self.assertTrue("item" in doc)
            self.assertTrue("instock" in doc)
            self.assertEqual(len(doc["instock"]), 2)

    @asyncio_test
    async def test_delete(self):
        db = self.db

        # Start Example 55
        await db.inventory.insert_many(
            [
                {
                    "item": "journal",
                    "qty": 25,
                    "size": {"h": 14, "w": 21, "uom": "cm"},
                    "status": "A",
                },
                {
                    "item": "notebook",
                    "qty": 50,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "P",
                },
                {
                    "item": "paper",
                    "qty": 100,
                    "size": {"h": 8.5, "w": 11, "uom": "in"},
                    "status": "D",
                },
                {
                    "item": "planner",
                    "qty": 75,
                    "size": {"h": 22.85, "w": 30, "uom": "cm"},
                    "status": "D",
                },
                {
                    "item": "postcard",
                    "qty": 45,
                    "size": {"h": 10, "w": 15.25, "uom": "cm"},
                    "status": "A",
                },
            ]
        )
        # End Example 55

        self.assertEqual(await db.inventory.count_documents({}), 5)

        # Start Example 57
        await db.inventory.delete_many({"status": "A"})
        # End Example 57

        self.assertEqual(await db.inventory.count_documents({}), 3)

        # Start Example 58
        await db.inventory.delete_one({"status": "D"})
        # End Example 58

        self.assertEqual(await db.inventory.count_documents({}), 2)

        # Start Example 56
        await db.inventory.delete_many({})
        # End Example 56

        self.assertEqual(await db.inventory.count_documents({}), 0)

    @env.require_version_min(3, 6)
    @env.require_replica_set
    @asyncio_test
    async def test_change_streams(self):
        db = self.db
        done = False

        async def insert_docs():
            while not done:
                await db.inventory.insert_one({"username": "alice"})
                await db.inventory.delete_one({"username": "alice"})

        task = asyncio.ensure_future(insert_docs())

        try:
            # Start Changestream Example 1
            cursor = db.inventory.watch()
            document = await cursor.next()
            # End Changestream Example 1

            # Start Changestream Example 2
            cursor = db.inventory.watch(full_document="updateLookup")
            document = await cursor.next()
            # End Changestream Example 2

            # Start Changestream Example 3
            resume_token = cursor.resume_token
            cursor = db.inventory.watch(resume_after=resume_token)
            document = await cursor.next()
            # End Changestream Example 3

            # Start Changestream Example 4
            pipeline = [
                {"$match": {"fullDocument.username": "alice"}},
                {"$addFields": {"newField": "this is an added field!"}},
            ]
            cursor = db.inventory.watch(pipeline=pipeline)
            document = await cursor.next()
            # End Changestream Example 4
        finally:
            done = True
            await task

    # $lookup was new in 3.2. The let and pipeline options were added in 3.6.
    @env.require_version_min(3, 6)
    @asyncio_test
    async def test_aggregate_examples(self):
        db = self.db

        # Start Aggregation Example 1
        cursor = db.sales.aggregate([{"$match": {"items.fruit": "banana"}}, {"$sort": {"date": 1}}])

        async for doc in cursor:
            print(doc)
        # End Aggregation Example 1

        # Start Aggregation Example 2
        cursor = db.sales.aggregate(
            [
                {"$unwind": "$items"},
                {"$match": {"items.fruit": "banana"}},
                {
                    "$group": {
                        "_id": {"day": {"$dayOfWeek": "$date"}},
                        "count": {"$sum": "$items.quantity"},
                    }
                },
                {"$project": {"dayOfWeek": "$_id.day", "numberSold": "$count", "_id": 0}},
                {"$sort": {"numberSold": 1}},
            ]
        )

        async for doc in cursor:
            print(doc)
        # End Aggregation Example 2

        # Start Aggregation Example 3
        cursor = db.sales.aggregate(
            [
                {"$unwind": "$items"},
                {
                    "$group": {
                        "_id": {"day": {"$dayOfWeek": "$date"}},
                        "items_sold": {"$sum": "$items.quantity"},
                        "revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.price"]}},
                    }
                },
                {
                    "$project": {
                        "day": "$_id.day",
                        "revenue": 1,
                        "items_sold": 1,
                        "discount": {
                            "$cond": {"if": {"$lte": ["$revenue", 250]}, "then": 25, "else": 0}
                        },
                    }
                },
            ]
        )

        async for doc in cursor:
            print(doc)
        # End Aggregation Example 3

        # Start Aggregation Example 4
        cursor = db.air_alliances.aggregate(
            [
                {
                    "$lookup": {
                        "from": "air_airlines",
                        "let": {"constituents": "$airlines"},
                        "pipeline": [{"$match": {"$expr": {"$in": ["$name", "$$constituents"]}}}],
                        "as": "airlines",
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "name": 1,
                        "airlines": {
                            "$filter": {
                                "input": "$airlines",
                                "as": "airline",
                                "cond": {"$eq": ["$$airline.country", "Canada"]},
                            }
                        },
                    }
                },
            ]
        )

        async for doc in cursor:
            print(doc)
        # End Aggregation Example 4

    @asyncio_test
    async def test_commands(self):
        db = self.db
        await db.restaurants.insert_one({})

        # Start runCommand Example 1
        info = await db.command("buildInfo")
        # End runCommand Example 1

        # Start runCommand Example 2
        stats = await db.command("collStats", "restaurants")
        # End runCommand Example 2

    @asyncio_test
    async def test_index_management(self):
        db = self.db

        # Start Index Example 1
        await db.records.create_index("score")
        # End Index Example 1

        # Start Index Example 1
        await db.restaurants.create_index(
            [("cuisine", pymongo.ASCENDING), ("name", pymongo.ASCENDING)],
            partialFilterExpression={"rating": {"$gt": 5}},
        )
        # End Index Example 1

    @env.require_version_min(3, 7)
    @env.require_replica_set
    @asyncio_test
    async def test_transactions(self):
        # Transaction examples
        self.addCleanup(env.sync_cx.drop_database, "hr")
        self.addCleanup(env.sync_cx.drop_database, "reporting")

        client = self.cx
        employees = self.cx.hr.employees
        events = self.cx.reporting.events
        await employees.insert_one({"employee": 3, "status": "Active"})
        await events.insert_one({"employee": 3, "status": {"new": "Active", "old": None}})

        # Start Transactions Intro Example 1

        async def update_employee_info(session):
            employees_coll = session.client.hr.employees
            events_coll = session.client.reporting.events

            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"), write_concern=WriteConcern(w="majority")
            ):
                await employees_coll.update_one(
                    {"employee": 3}, {"$set": {"status": "Inactive"}}, session=session
                )
                await events_coll.insert_one(
                    {"employee": 3, "status": {"new": "Inactive", "old": "Active"}}, session=session
                )

                while True:
                    try:
                        # Commit uses write concern set at transaction start.
                        await session.commit_transaction()
                        print("Transaction committed.")
                        break
                    except (ConnectionFailure, OperationFailure) as exc:
                        # Can retry commit
                        if exc.has_error_label("UnknownTransactionCommitResult"):
                            print("UnknownTransactionCommitResult, retrying commit operation ...")
                            continue
                        else:
                            print("Error during commit ...")
                            raise

        # End Transactions Intro Example 1

        # Test the example.
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            async with await client.start_session() as s:
                await update_employee_info(s)

        employee = await employees.find_one({"employee": 3})
        self.assertIsNotNone(employee)
        self.assertEqual(employee["status"], "Inactive")
        self.assertIn("Transaction committed", mock_stdout.getvalue())

        # Start Transactions Retry Example 1
        async def run_transaction_with_retry(txn_coro, session):
            while True:
                try:
                    await txn_coro(session)  # performs transaction
                    break
                except (ConnectionFailure, OperationFailure) as exc:
                    print("Transaction aborted. Caught exception during transaction.")

                    # If transient error, retry the whole transaction
                    if exc.has_error_label("TransientTransactionError"):
                        print("TransientTransactionError, retryin transaction ...")
                        continue
                    else:
                        raise

        # End Transactions Retry Example 1

        # Test the example.
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            async with await client.start_session() as s:
                await run_transaction_with_retry(update_employee_info, s)

        employee = await employees.find_one({"employee": 3})
        self.assertIsNotNone(employee)
        self.assertEqual(employee["status"], "Inactive")
        self.assertIn("Transaction committed", mock_stdout.getvalue())

        # Start Transactions Retry Example 2
        async def commit_with_retry(session):
            while True:
                try:
                    # Commit uses write concern set at transaction start.
                    await session.commit_transaction()
                    print("Transaction committed.")
                    break
                except (ConnectionFailure, OperationFailure) as exc:
                    # Can retry commit
                    if exc.has_error_label("UnknownTransactionCommitResult"):
                        print("UnknownTransactionCommitResult, retrying commit operation ...")
                        continue
                    else:
                        print("Error during commit ...")
                        raise

        # End Transactions Retry Example 2

        # Test commit_with_retry from the previous examples
        async def _insert_employee_retry_commit(session):
            async with session.start_transaction():
                await employees.insert_one({"employee": 4, "status": "Active"}, session=session)
                await events.insert_one(
                    {"employee": 4, "status": {"new": "Active", "old": None}}, session=session
                )

                await commit_with_retry(session)

        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            async with await client.start_session() as s:
                await run_transaction_with_retry(_insert_employee_retry_commit, s)

        employee = await employees.find_one({"employee": 4})
        self.assertIsNotNone(employee)
        self.assertEqual(employee["status"], "Active")
        self.assertIn("Transaction committed", mock_stdout.getvalue())

        # Start Transactions Retry Example 3

        async def run_transaction_with_retry(txn_coro, session):
            while True:
                try:
                    await txn_coro(session)  # performs transaction
                    break
                except (ConnectionFailure, OperationFailure) as exc:
                    # If transient error, retry the whole transaction
                    if exc.has_error_label("TransientTransactionError"):
                        print("TransientTransactionError, retrying transaction ...")
                        continue
                    else:
                        raise

        async def commit_with_retry(session):
            while True:
                try:
                    # Commit uses write concern set at transaction start.
                    await session.commit_transaction()
                    print("Transaction committed.")
                    break
                except (ConnectionFailure, OperationFailure) as exc:
                    # Can retry commit
                    if exc.has_error_label("UnknownTransactionCommitResult"):
                        print("UnknownTransactionCommitResult, retrying commit operation ...")
                        continue
                    else:
                        print("Error during commit ...")
                        raise

        # Updates two collections in a transactions

        async def update_employee_info(session):
            employees_coll = session.client.hr.employees
            events_coll = session.client.reporting.events

            async with session.start_transaction(
                read_concern=ReadConcern("snapshot"),
                write_concern=WriteConcern(w="majority"),
                read_preference=ReadPreference.PRIMARY,
            ):
                await employees_coll.update_one(
                    {"employee": 3}, {"$set": {"status": "Inactive"}}, session=session
                )
                await events_coll.insert_one(
                    {"employee": 3, "status": {"new": "Inactive", "old": "Active"}}, session=session
                )

                await commit_with_retry(session)

        # Start a session.
        async with await client.start_session() as session:
            try:
                await run_transaction_with_retry(update_employee_info, session)
            except Exception as exc:
                # Do something with error.
                raise

        # End Transactions Retry Example 3

        employee = await employees.find_one({"employee": 3})
        self.assertIsNotNone(employee)
        self.assertEqual(employee["status"], "Inactive")

        AsyncIOMotorClient = lambda _: self.cx
        uriString = None

        # Start Transactions withTxn API Example 1

        # For a replica set, include the replica set name and a seedlist of the members in the URI string; e.g.
        # uriString = 'mongodb://mongodb0.example.com:27017,mongodb1.example.com:27017/?replicaSet=myRepl'
        # For a sharded cluster, connect to the mongos instances; e.g.
        # uriString = 'mongodb://mongos0.example.com:27017,mongos1.example.com:27017/'

        client = AsyncIOMotorClient(uriString)
        wc_majority = WriteConcern("majority", wtimeout=1000)

        # Prereq: Create collections.
        await client.get_database("mydb1", write_concern=wc_majority).foo.insert_one({"abc": 0})
        await client.get_database("mydb2", write_concern=wc_majority).bar.insert_one({"xyz": 0})

        # Step 1: Define the callback that specifies the sequence of operations to perform inside the transactions.
        async def callback(my_session):
            collection_one = my_session.client.mydb1.foo
            collection_two = my_session.client.mydb2.bar

            # Important:: You must pass the session to the operations.
            await collection_one.insert_one({"abc": 1}, session=my_session)
            await collection_two.insert_one({"xyz": 999}, session=my_session)

        # Step 2: Start a client session.
        async with await client.start_session() as session:
            # Step 3: Use with_transaction to start a transaction, execute the callback, and commit (or abort on error).
            await session.with_transaction(
                callback,
                read_concern=ReadConcern("local"),
                write_concern=wc_majority,
                read_preference=ReadPreference.PRIMARY,
            )

        # End Transactions withTxn API Example 1

    @env.require_version_min(3, 6)
    @env.require_replica_set
    @asyncio_test
    async def test_causal_consistency(self):
        # Causal consistency examples
        client = self.cx
        self.addCleanup(env.sync_cx.drop_database, "test")
        await client.test.drop_collection("items")
        await client.test.items.insert_one(
            {"sku": "111", "name": "Peanuts", "start": datetime.datetime.today()}
        )

        # Start Causal Consistency Example 1
        async with await client.start_session(causal_consistency=True) as s1:
            current_date = datetime.datetime.today()
            items = client.get_database(
                "test",
                read_concern=ReadConcern("majority"),
                write_concern=WriteConcern("majority", wtimeout=1000),
            ).items
            await items.update_one(
                {"sku": "111", "end": None}, {"$set": {"end": current_date}}, session=s1
            )
            await items.insert_one(
                {"sku": "nuts-111", "name": "Pecans", "start": current_date}, session=s1
            )
        # End Causal Consistency Example 1

        # Start Causal Consistency Example 2
        async with await client.start_session(causal_consistency=True) as s2:
            s2.advance_cluster_time(s1.cluster_time)
            s2.advance_operation_time(s1.operation_time)

            items = client.get_database(
                "test",
                read_preference=ReadPreference.SECONDARY,
                read_concern=ReadConcern("majority"),
                write_concern=WriteConcern("majority", wtimeout=1000),
            ).items
            async for item in items.find({"end": None}, session=s2):
                print(item)
        # End Causal Consistency Example 2

    @env.require_version_min(4, 7)
    @asyncio_test
    async def test_versioned_api(self):
        # Versioned API examples
        # Use connect=False to reduce overhead as client is not used to run
        # any operations.
        AsyncIOMotorClient = lambda _, server_api: self.asyncio_client(
            server_api=server_api, connect=False
        )
        uri = None

        # Start Versioned API Example 1
        from pymongo.server_api import ServerApi

        client = AsyncIOMotorClient(uri, server_api=ServerApi("1"))
        # End Versioned API Example 1

        # Start Versioned API Example 2
        client = AsyncIOMotorClient(uri, server_api=ServerApi("1", strict=True))
        # End Versioned API Example 2

        # Start Versioned API Example 3
        client = AsyncIOMotorClient(uri, server_api=ServerApi("1", strict=False))
        # End Versioned API Example 3

        # Start Versioned API Example 4
        client = AsyncIOMotorClient(uri, server_api=ServerApi("1", deprecation_errors=True))
        # End Versioned API Example 4

    @unittest.skip("MOTOR-908 count has been added to API version 1")
    @env.require_version_min(4, 7)
    # Only run on RS until https://jira.mongodb.org/browse/SERVER-58785 is resolved.
    @env.require_replica_set
    @asyncio_test
    async def test_versioned_api_migration(self):
        client = self.asyncio_client(server_api=ServerApi("1", strict=True))
        await client.db.sales.drop()

        # Start Versioned API Example 5
        def strptime(s):
            return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

        await client.db.sales.insert_many(
            [
                {
                    "_id": 1,
                    "item": "abc",
                    "price": 10,
                    "quantity": 2,
                    "date": strptime("2021-01-01T08:00:00Z"),
                },
                {
                    "_id": 2,
                    "item": "jkl",
                    "price": 20,
                    "quantity": 1,
                    "date": strptime("2021-02-03T09:00:00Z"),
                },
                {
                    "_id": 3,
                    "item": "xyz",
                    "price": 5,
                    "quantity": 5,
                    "date": strptime("2021-02-03T09:05:00Z"),
                },
                {
                    "_id": 4,
                    "item": "abc",
                    "price": 10,
                    "quantity": 10,
                    "date": strptime("2021-02-15T08:00:00Z"),
                },
                {
                    "_id": 5,
                    "item": "xyz",
                    "price": 5,
                    "quantity": 10,
                    "date": strptime("2021-02-15T09:05:00Z"),
                },
                {
                    "_id": 6,
                    "item": "xyz",
                    "price": 5,
                    "quantity": 5,
                    "date": strptime("2021-02-15T12:05:10Z"),
                },
                {
                    "_id": 7,
                    "item": "xyz",
                    "price": 5,
                    "quantity": 10,
                    "date": strptime("2021-02-15T14:12:12Z"),
                },
                {
                    "_id": 8,
                    "item": "abc",
                    "price": 10,
                    "quantity": 5,
                    "date": strptime("2021-03-16T20:20:13Z"),
                },
            ]
        )
        # End Versioned API Example 5

        with self.assertRaisesRegex(
            OperationFailure,
            "Provided apiStrict:true, but the command count is not in API Version 1",
        ):
            await client.db.command("count", "sales", query={})

        # Start Versioned API Example 6
        # pymongo.errors.OperationFailure: Provided apiStrict:true, but the command count is not in API Version 1, full error: {'ok': 0.0, 'errmsg': 'Provided apiStrict:true, but the command count is not in API Version 1', 'code': 323, 'codeName': 'APIStrictError'}
        # End Versioned API Example 6

        # Start Versioned API Example 7
        await client.db.sales.count_documents({})
        # End Versioned API Example 7

        # Start Versioned API Example 8
        # 8
        # End Versioned API Example 8

    @env.require_version_min(5, 0)
    @asyncio_test
    async def test_snapshot_query(self):
        client = self.cx
        if not env.is_replica_set and not env.is_mongos:
            self.skipTest("Must be a sharded or replicaset")

        self.addCleanup(client.drop_database, "pets")
        db = client.pets
        await db.drop_collection("cats")
        await db.drop_collection("dogs")
        await db.cats.insert_one(
            {"name": "Whiskers", "color": "white", "age": 10, "adoptable": True}
        )
        await db.dogs.insert_one(
            {"name": "Pebbles", "color": "Brown", "age": 10, "adoptable": True}
        )
        await wait_until(lambda: self.check_for_snapshot(db.cats), "success")
        await wait_until(lambda: self.check_for_snapshot(db.dogs), "success")

        # Start Snapshot Query Example 1

        db = client.pets
        async with await client.start_session(snapshot=True) as s:
            adoptablePetsCount = 0
            docs = await db.cats.aggregate(
                [{"$match": {"adoptable": True}}, {"$count": "adoptableCatsCount"}], session=s
            ).to_list(None)
            adoptablePetsCount = docs[0]["adoptableCatsCount"]

            docs = await db.dogs.aggregate(
                [{"$match": {"adoptable": True}}, {"$count": "adoptableDogsCount"}], session=s
            ).to_list(None)
            adoptablePetsCount += docs[0]["adoptableDogsCount"]

        print(adoptablePetsCount)

        # End Snapshot Query Example 1
        db = client.retail
        self.addCleanup(client.drop_database, "retail")
        await db.drop_collection("sales")

        saleDate = datetime.datetime.now()
        await db.sales.insert_one({"shoeType": "boot", "price": 30, "saleDate": saleDate})
        await wait_until(lambda: self.check_for_snapshot(db.sales), "success")

        # Start Snapshot Query Example 2
        db = client.retail
        async with await client.start_session(snapshot=True) as s:
            docs = await db.sales.aggregate(
                [
                    {
                        "$match": {
                            "$expr": {
                                "$gt": [
                                    "$saleDate",
                                    {
                                        "$dateSubtract": {
                                            "startDate": "$$NOW",
                                            "unit": "day",
                                            "amount": 1,
                                        }
                                    },
                                ]
                            }
                        }
                    },
                    {"$count": "totalDailySales"},
                ],
                session=s,
            ).to_list(None)
            total = docs[0]["totalDailySales"]

            print(total)

        # End Snapshot Query Example 2

    async def check_for_snapshot(self, collection):
        """Wait for snapshot reads to become available to prevent this error:
        [246:SnapshotUnavailable]: Unable to read from a snapshot due to pending collection catalog changes; please retry the operation. Snapshot timestamp is Timestamp(1646666892, 4). Collection minimum is Timestamp(1646666892, 5) (on localhost:27017, modern retry, attempt 1)
        From https://github.com/mongodb/mongo-ruby-driver/commit/7c4117b58e3d12e237f7536f7521e18fc15f79ac
        """
        client = collection.database.client
        async with await client.start_session(snapshot=True) as s:
            try:
                await collection.aggregate([], session=s).to_list(None)
                return True
            except OperationFailure as e:
                # Retry them as the server demands...
                if e.code == 246:  # SnapshotUnavailable
                    return False
                raise


LOCAL_MASTER_KEY = base64.b64decode(
    b"Mng0NCt4ZHVUYUJCa1kxNkVyNUR1QURhZ2h2UzR2d2RrZzh0cFBwM3R6NmdWMDFBMUN3YkQ"
    b"5aXRRMkhGRGdQV09wOGVNYUMxT2k3NjZKelhaQmRCZGJkTXVyZG9uSjFk"
)


class TestQueryableEncryptionDocsExample(AsyncIOTestCase):

    # Queryable Encryption is not supported on Standalone topology.

    @env.require_version_min(6, 0)
    @asyncio_test
    @env.require_replica_set
    async def test_queryable_encryption(self):
        client = self.cx

        # MongoClient to use in testing that handles auth/tls/etc,
        # and cleanup.
        def MongoClient(**kwargs):
            c = self.asyncio_client(**kwargs)
            self.addCleanup(c.close)
            return c

        # Drop data from prior test runs.
        await client.keyvault.datakeys.drop()
        await client.drop_database("docs_examples")

        kms_providers_map = {"local": {"key": LOCAL_MASTER_KEY}}

        # Create two data keys.
        key_vault_client = MongoClient()
        await key_vault_client.admin.command("ping")
        client_encryption = AsyncIOMotorClientEncryption(
            kms_providers_map, "keyvault.datakeys", key_vault_client, CodecOptions()
        )
        key1_id = await client_encryption.create_data_key("local")
        key2_id = await client_encryption.create_data_key("local")

        # Create an encryptedFieldsMap.
        encrypted_fields_map = {
            "docs_examples.encrypted": {
                "fields": [
                    {
                        "path": "encrypted_indexed",
                        "bsonType": "string",
                        "keyId": key1_id,
                        "queries": [
                            {
                                "queryType": "equality",
                            },
                        ],
                    },
                    {
                        "path": "encrypted_unindexed",
                        "bsonType": "string",
                        "keyId": key2_id,
                    },
                ],
            },
        }

        # Create an Queryable Encryption collection.
        opts = AutoEncryptionOpts(
            kms_providers_map, "keyvault.datakeys", encrypted_fields_map=encrypted_fields_map
        )
        encrypted_client = MongoClient(auto_encryption_opts=opts)

        # Create a Queryable Encryption collection "docs_examples.encrypted".
        # Because docs_examples.encrypted is in encrypted_fields_map, it is
        # created with Queryable Encryption support.
        db = encrypted_client.docs_examples
        encrypted_coll = await db.create_collection("encrypted")

        # Auto encrypt an insert and find.

        # Encrypt an insert.
        await encrypted_coll.insert_one(
            {
                "_id": 1,
                "encrypted_indexed": "indexed_value",
                "encrypted_unindexed": "unindexed_value",
            }
        )

        # Encrypt a find.
        res = await encrypted_coll.find_one({"encrypted_indexed": "indexed_value"})
        assert res is not None
        assert res["encrypted_indexed"] == "indexed_value"
        assert res["encrypted_unindexed"] == "unindexed_value"

        # Find documents without decryption.
        unencrypted_client = MongoClient()
        unencrypted_coll = unencrypted_client.docs_examples.encrypted
        res = await unencrypted_coll.find_one({"_id": 1})
        assert res is not None
        assert isinstance(res["encrypted_indexed"], Binary)
        assert isinstance(res["encrypted_unindexed"], Binary)

        await client_encryption.close()
