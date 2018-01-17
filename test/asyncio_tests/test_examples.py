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

from test import env
from test.asyncio_tests import AsyncIOTestCase, asyncio_test


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
            {"item": "canvas",
             "qty": 100,
             "tags": ["cotton"],
             "size": {"h": 28, "w": 35.5, "uom": "cm"}})
        # End Example 1

        self.assertEqual(await db.inventory.count(), 1)

        # Start Example 2
        cursor = db.inventory.find({"item": "canvas"})
        # End Example 2

        self.assertEqual(await cursor.count(), 1)

        # Start Example 3
        await db.inventory.insert_many([
            {"item": "journal",
             "qty": 25,
             "tags": ["blank", "red"],
             "size": {"h": 14, "w": 21, "uom": "cm"}},
            {"item": "mat",
             "qty": 85,
             "tags": ["gray"],
             "size": {"h": 27.9, "w": 35.5, "uom": "cm"}},
            {"item": "mousepad",
             "qty": 25,
             "tags": ["gel", "blue"],
             "size": {"h": 19, "w": 22.85, "uom": "cm"}}])
        # End Example 3

        self.assertEqual(await db.inventory.count(), 4)

    @asyncio_test
    async def test_query_top_level_fields(self):
        db = self.db

        # Start Example 6
        await db.inventory.insert_many([
            {"item": "journal",
             "qty": 25,
             "size": {"h": 14, "w": 21, "uom": "cm"},
             "status": "A"},
            {"item": "notebook",
             "qty": 50,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "A"},
            {"item": "paper",
             "qty": 100,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "D"},
            {"item": "planner",
             "qty": 75, "size": {"h": 22.85, "w": 30, "uom": "cm"},
             "status": "D"},
            {"item": "postcard",
             "qty": 45,
             "size": {"h": 10, "w": 15.25, "uom": "cm"},
             "status": "A"}])
        # End Example 6

        self.assertEqual(await db.inventory.count(), 5)

        # Start Example 7
        cursor = db.inventory.find({})
        # End Example 7

        self.assertEqual(await cursor.count(), 5)

        # Start Example 9
        cursor = db.inventory.find({"status": "D"})
        # End Example 9

        self.assertEqual(await cursor.count(), 2)

        # Start Example 10
        cursor = db.inventory.find({"status": {"$in": ["A", "D"]}})
        # End Example 10

        self.assertEqual(await cursor.count(), 5)

        # Start Example 11
        cursor = db.inventory.find({"status": "A", "qty": {"$lt": 30}})
        # End Example 11

        self.assertEqual(await cursor.count(), 1)

        # Start Example 12
        cursor = db.inventory.find(
            {"$or": [{"status": "A"}, {"qty": {"$lt": 30}}]})
        # End Example 12

        self.assertEqual(await cursor.count(), 3)

        # Start Example 13
        cursor = db.inventory.find({
            "status": "A",
            "$or": [{"qty": {"$lt": 30}}, {"item": {"$regex": "^p"}}]})
        # End Example 13

        self.assertEqual(await cursor.count(), 2)

    @asyncio_test
    async def test_query_embedded_documents(self):
        db = self.db

        # Start Example 14
        # Subdocument key order matters in a few of these examples so we have
        # to use bson.son.SON instead of a Python dict.
        from bson.son import SON
        await db.inventory.insert_many([
            {"item": "journal",
             "qty": 25,
             "size": SON([("h", 14), ("w", 21), ("uom", "cm")]),
             "status": "A"},
            {"item": "notebook",
             "qty": 50,
             "size": SON([("h", 8.5), ("w", 11), ("uom", "in")]),
             "status": "A"},
            {"item": "paper",
             "qty": 100,
             "size": SON([("h", 8.5), ("w", 11), ("uom", "in")]),
             "status": "D"},
            {"item": "planner",
             "qty": 75,
             "size": SON([("h", 22.85), ("w", 30), ("uom", "cm")]),
             "status": "D"},
            {"item": "postcard",
             "qty": 45,
             "size": SON([("h", 10), ("w", 15.25), ("uom", "cm")]),
             "status": "A"}])
        # End Example 14

        # Start Example 15
        cursor = db.inventory.find(
            {"size": SON([("h", 14), ("w", 21), ("uom", "cm")])})
        # End Example 15

        self.assertEqual(await cursor.count(), 1)

        # Start Example 16
        cursor = db.inventory.find(
            {"size": SON([("w", 21), ("h", 14), ("uom", "cm")])})
        # End Example 16

        self.assertEqual(await cursor.count(), 0)

        # Start Example 17
        cursor = db.inventory.find({"size.uom": "in"})
        # End Example 17

        self.assertEqual(await cursor.count(), 2)

        # Start Example 18
        cursor = db.inventory.find({"size.h": {"$lt": 15}})
        # End Example 18

        self.assertEqual(await cursor.count(), 4)

        # Start Example 19
        cursor = db.inventory.find(
            {"size.h": {"$lt": 15}, "size.uom": "in", "status": "D"})
        # End Example 19

        self.assertEqual(await cursor.count(), 1)

    @asyncio_test
    async def test_query_arrays(self):
        db = self.db

        # Start Example 20
        await db.inventory.insert_many([
            {"item": "journal",
             "qty": 25,
             "tags": ["blank", "red"],
             "dim_cm": [14, 21]},
            {"item": "notebook",
             "qty": 50,
             "tags": ["red", "blank"],
             "dim_cm": [14, 21]},
            {"item": "paper",
             "qty": 100,
             "tags": ["red", "blank", "plain"],
             "dim_cm": [14, 21]},
            {"item": "planner",
             "qty": 75,
             "tags": ["blank", "red"],
             "dim_cm": [22.85, 30]},
            {"item": "postcard",
             "qty": 45,
             "tags": ["blue"],
             "dim_cm": [10, 15.25]}])
        # End Example 20

        # Start Example 21
        cursor = db.inventory.find({"tags": ["red", "blank"]})
        # End Example 21

        self.assertEqual(await cursor.count(), 1)

        # Start Example 22
        cursor = db.inventory.find({"tags": {"$all": ["red", "blank"]}})
        # End Example 22

        self.assertEqual(await cursor.count(), 4)

        # Start Example 23
        cursor = db.inventory.find({"tags": "red"})
        # End Example 23

        self.assertEqual(await cursor.count(), 4)

        # Start Example 24
        cursor = db.inventory.find({"dim_cm": {"$gt": 25}})
        # End Example 24

        self.assertEqual(await cursor.count(), 1)

        # Start Example 25
        cursor = db.inventory.find({"dim_cm": {"$gt": 15, "$lt": 20}})
        # End Example 25

        self.assertEqual(await cursor.count(), 4)

        # Start Example 26
        cursor = db.inventory.find(
            {"dim_cm": {"$elemMatch": {"$gt": 22, "$lt": 30}}})
        # End Example 26

        self.assertEqual(await cursor.count(), 1)

        # Start Example 27
        cursor = db.inventory.find({"dim_cm.1": {"$gt": 25}})
        # End Example 27

        self.assertEqual(await cursor.count(), 1)

        # Start Example 28
        cursor = db.inventory.find({"tags": {"$size": 3}})
        # End Example 28

        self.assertEqual(await cursor.count(), 1)

    @asyncio_test
    async def test_query_array_of_documents(self):
        db = self.db

        # Start Example 29
        # Subdocument key order matters in a few of these examples so we have
        # to use bson.son.SON instead of a Python dict.
        from bson.son import SON
        await db.inventory.insert_many([
            {"item": "journal",
             "instock": [
                 SON([("warehouse", "A"), ("qty", 5)]),
                 SON([("warehouse", "C"), ("qty", 15)])]},
            {"item": "notebook",
             "instock": [
                 SON([("warehouse", "C"), ("qty", 5)])]},
            {"item": "paper",
             "instock": [
                 SON([("warehouse", "A"), ("qty", 60)]),
                 SON([("warehouse", "B"), ("qty", 15)])]},
            {"item": "planner",
             "instock": [
                 SON([("warehouse", "A"), ("qty", 40)]),
                 SON([("warehouse", "B"), ("qty", 5)])]},
            {"item": "postcard",
             "instock": [
                 SON([("warehouse", "B"), ("qty", 15)]),
                 SON([("warehouse", "C"), ("qty", 35)])]}])
        # End Example 29

        # Start Example 30
        cursor = db.inventory.find(
            {"instock": SON([("warehouse", "A"), ("qty", 5)])})
        # End Example 30

        self.assertEqual(await cursor.count(), 1)

        # Start Example 31
        cursor = db.inventory.find(
            {"instock": SON([("qty", 5), ("warehouse", "A")])})
        # End Example 31

        self.assertEqual(await cursor.count(), 0)

        # Start Example 32
        cursor = db.inventory.find({'instock.0.qty': {"$lte": 20}})
        # End Example 32

        self.assertEqual(await cursor.count(), 3)

        # Start Example 33
        cursor = db.inventory.find({'instock.qty': {"$lte": 20}})
        # End Example 33

        self.assertEqual(await cursor.count(), 5)

        # Start Example 34
        cursor = db.inventory.find(
            {"instock": {"$elemMatch": {"qty": 5, "warehouse": "A"}}})
        # End Example 34

        self.assertEqual(await cursor.count(), 1)

        # Start Example 35
        cursor = db.inventory.find(
            {"instock": {"$elemMatch": {"qty": {"$gt": 10, "$lte": 20}}}})
        # End Example 35

        self.assertEqual(await cursor.count(), 3)

        # Start Example 36
        cursor = db.inventory.find({"instock.qty": {"$gt": 10, "$lte": 20}})
        # End Example 36

        self.assertEqual(await cursor.count(), 4)

        # Start Example 37
        cursor = db.inventory.find(
            {"instock.qty": 5, "instock.warehouse": "A"})
        # End Example 37

        self.assertEqual(await cursor.count(), 2)

    @asyncio_test
    async def test_query_null(self):
        db = self.db

        # Start Example 38
        await db.inventory.insert_many([{"_id": 1, "item": None}, {"_id": 2}])
        # End Example 38

        # Start Example 39
        cursor = db.inventory.find({"item": None})
        # End Example 39

        self.assertEqual(await cursor.count(), 2)

        # Start Example 40
        cursor = db.inventory.find({"item": {"$type": 10}})
        # End Example 40

        self.assertEqual(await cursor.count(), 1)

        # Start Example 41
        cursor = db.inventory.find({"item": {"$exists": False}})
        # End Example 41

        self.assertEqual(await cursor.count(), 1)

    @asyncio_test
    async def test_projection(self):
        db = self.db

        # Start Example 42
        await db.inventory.insert_many([
            {"item": "journal",
             "status": "A",
             "size": {"h": 14, "w": 21, "uom": "cm"},
             "instock": [{"warehouse": "A", "qty": 5}]},
            {"item": "notebook",
             "status": "A",
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "instock": [{"warehouse": "C", "qty": 5}]},
            {"item": "paper",
             "status": "D",
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "instock": [{"warehouse": "A", "qty": 60}]},
            {"item": "planner",
             "status": "D",
             "size": {"h": 22.85, "w": 30, "uom": "cm"},
             "instock": [{"warehouse": "A", "qty": 40}]},
            {"item": "postcard",
             "status": "A",
             "size": {"h": 10, "w": 15.25, "uom": "cm"},
             "instock": [
                 {"warehouse": "B", "qty": 15},
                 {"warehouse": "C", "qty": 35}]}])
        # End Example 42

        # Start Example 43
        cursor = db.inventory.find({"status": "A"})
        # End Example 43

        self.assertEqual(await cursor.count(), 3)

        # Start Example 44
        cursor = db.inventory.find(
            {"status": "A"}, {"item": 1, "status": 1})
        # End Example 44

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 45
        cursor = db.inventory.find(
            {"status": "A"}, {"item": 1, "status": 1, "_id": 0})
        # End Example 45

        async for doc in cursor:
            self.assertFalse("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 46
        cursor = db.inventory.find(
            {"status": "A"}, {"status": 0, "instock": 0})
        # End Example 46

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertFalse("status" in doc)
            self.assertTrue("size" in doc)
            self.assertFalse("instock" in doc)

        # Start Example 47
        cursor = db.inventory.find(
            {"status": "A"}, {"item": 1, "status": 1, "size.uom": 1})
        # End Example 47

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertTrue("size" in doc)
            self.assertFalse("instock" in doc)
            size = doc['size']
            self.assertTrue('uom' in size)
            self.assertFalse('h' in size)
            self.assertFalse('w' in size)

        # Start Example 48
        cursor = db.inventory.find({"status": "A"}, {"size.uom": 0})
        # End Example 48

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertTrue("size" in doc)
            self.assertTrue("instock" in doc)
            size = doc['size']
            self.assertFalse('uom' in size)
            self.assertTrue('h' in size)
            self.assertTrue('w' in size)

        # Start Example 49
        cursor = db.inventory.find(
            {"status": "A"}, {"item": 1, "status": 1, "instock.qty": 1})
        # End Example 49

        async for doc in cursor:
            self.assertTrue("_id" in doc)
            self.assertTrue("item" in doc)
            self.assertTrue("status" in doc)
            self.assertFalse("size" in doc)
            self.assertTrue("instock" in doc)
            for subdoc in doc['instock']:
                self.assertFalse('warehouse' in subdoc)
                self.assertTrue('qty' in subdoc)

        # Start Example 50
        cursor = db.inventory.find(
            {"status": "A"},
            {"item": 1, "status": 1, "instock": {"$slice": -1}})
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
        await db.inventory.insert_many([
            {"item": "canvas",
             "qty": 100,
             "size": {"h": 28, "w": 35.5, "uom": "cm"},
             "status": "A"},
            {"item": "journal",
             "qty": 25,
             "size": {"h": 14, "w": 21, "uom": "cm"},
             "status": "A"},
            {"item": "mat",
             "qty": 85,
             "size": {"h": 27.9, "w": 35.5, "uom": "cm"},
             "status": "A"},
            {"item": "mousepad",
             "qty": 25,
             "size": {"h": 19, "w": 22.85, "uom": "cm"},
             "status": "P"},
            {"item": "notebook",
             "qty": 50,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "P"},
            {"item": "paper",
             "qty": 100,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "D"},
            {"item": "planner",
             "qty": 75,
             "size": {"h": 22.85, "w": 30, "uom": "cm"},
             "status": "D"},
            {"item": "postcard",
             "qty": 45,
             "size": {"h": 10, "w": 15.25, "uom": "cm"},
             "status": "A"},
            {"item": "sketchbook",
             "qty": 80,
             "size": {"h": 14, "w": 21, "uom": "cm"},
             "status": "A"},
            {"item": "sketch pad",
             "qty": 95,
             "size": {"h": 22.85, "w": 30.5, "uom": "cm"},
             "status": "A"}])
        # End Example 51

        # Start Example 52
        await db.inventory.update_one(
            {"item": "paper"},
            {"$set": {"size.uom": "cm", "status": "P"},
             "$currentDate": {"lastModified": True}})
        # End Example 52

        async for doc in db.inventory.find({"item": "paper"}):
            self.assertEqual(doc["size"]["uom"], "cm")
            self.assertEqual(doc["status"], "P")
            self.assertTrue("lastModified" in doc)

        # Start Example 53
        await db.inventory.update_many(
            {"qty": {"$lt": 50}},
            {"$set": {"size.uom": "in", "status": "P"},
             "$currentDate": {"lastModified": True}})
        # End Example 53

        async for doc in db.inventory.find({"qty": {"$lt": 50}}):
            self.assertEqual(doc["size"]["uom"], "in")
            self.assertEqual(doc["status"], "P")
            self.assertTrue("lastModified" in doc)

        # Start Example 54
        await db.inventory.replace_one(
            {"item": "paper"},
            {"item": "paper",
             "instock": [
                 {"warehouse": "A", "qty": 60},
                 {"warehouse": "B", "qty": 40}]})
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
        await db.inventory.insert_many([
            {"item": "journal",
             "qty": 25,
             "size": {"h": 14, "w": 21, "uom": "cm"},
             "status": "A"},
            {"item": "notebook",
             "qty": 50,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "P"},
            {"item": "paper",
             "qty": 100,
             "size": {"h": 8.5, "w": 11, "uom": "in"},
             "status": "D"},
            {"item": "planner",
             "qty": 75,
             "size": {"h": 22.85, "w": 30, "uom": "cm"},
             "status": "D"},
            {"item": "postcard",
             "qty": 45,
             "size": {"h": 10, "w": 15.25, "uom": "cm"},
             "status": "A"}])
        # End Example 55

        self.assertEqual(await db.inventory.count(), 5)

        # Start Example 57
        await db.inventory.delete_many({"status": "A"})
        # End Example 57

        self.assertEqual(await db.inventory.count(), 3)

        # Start Example 58
        await db.inventory.delete_one({"status": "D"})
        # End Example 58

        self.assertEqual(await db.inventory.count(), 2)

        # Start Example 56
        await db.inventory.delete_many({})
        # End Example 56

        self.assertEqual(await db.inventory.count(), 0)

    @env.require_version_min(3, 6)
    @env.require_replica_set
    @asyncio_test
    async def test_change_streams(self):
        db = self.db
        done = False

        async def insert_docs():
            while not done:
                await db.inventory.insert_one({})
                await asyncio.sleep(0.1)

        task = asyncio.ensure_future(insert_docs())

        try:
            # Start Changestream Example 1
            cursor = db.inventory.watch()
            document = await cursor.next()
            # End Changestream Example 1

            # Start Changestream Example 2
            cursor = db.inventory.watch(full_document='updateLookup')
            document = await cursor.next()
            # End Changestream Example 2

            # Start Changestream Example 3
            resume_token = document.get("_id")
            cursor = db.inventory.watch(resume_after=resume_token)
            document = await cursor.next()

            # End Changestream Example 3
        finally:
            done = True
            await task
