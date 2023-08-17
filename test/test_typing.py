# Copyright 2023-present MongoDB, Inc.
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

"""Test that each file in mypy_fails/ actually fails mypy, and test some
sample client code that uses Motor typings.
"""
import unittest
from test.asyncio_tests import AsyncIOTestCase, asyncio_test
from typing import TYPE_CHECKING, Any, AsyncIterable, Dict, List, Union

from bson import CodecOptions
from bson.raw_bson import RawBSONDocument
from bson.son import SON
from pymongo.operations import DeleteOne, InsertOne, ReplaceOne
from pymongo.read_preferences import ReadPreference

from motor.core import AgnosticClient, AgnosticCollection

try:
    from bson import ObjectId
    from typing_extensions import NotRequired, TypedDict

    class Movie(TypedDict):
        name: str
        year: int

    class MovieWithId(TypedDict):
        _id: ObjectId
        name: str
        year: int

    class ImplicitMovie(TypedDict):
        _id: NotRequired[ObjectId]
        name: str
        year: int

except ImportError:
    Movie = dict  # type:ignore[misc,assignment]
    ImplicitMovie = dict  # type: ignore[assignment,misc]
    MovieWithId = dict  # type: ignore[assignment,misc]
    TypedDict = None
    NotRequired = None  # type: ignore[assignment]


def only_type_check(func):
    def inner(*args, **kwargs):
        if not TYPE_CHECKING:
            raise unittest.SkipTest("Used for Type Checking Only")
        func(*args, **kwargs)

    return inner


class TestMotor(AsyncIOTestCase):
    cx: AgnosticClient

    @asyncio_test
    async def test_insert_find(self) -> None:
        doc = {"my": "doc"}
        coll: AgnosticCollection = self.collection
        coll2 = self.cx.test.test2
        result = await coll.insert_one(doc)
        self.assertEqual(result.inserted_id, doc["_id"])
        retrieved = await coll.find_one({"_id": doc["_id"]})
        if retrieved:
            # Documents returned from find are mutable.
            retrieved["new_field"] = 1
            result2 = await coll2.insert_one(retrieved)
            self.assertEqual(result2.inserted_id, result.inserted_id)

    @asyncio_test
    async def test_cursor_iterable(self) -> None:
        async def to_list(iterable: AsyncIterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
            return [gen async for gen in iterable]

        await self.collection.insert_one({})
        cursor = self.collection.find()
        docs = await to_list(cursor)
        self.assertTrue(docs)

    @only_type_check
    @asyncio_test
    async def test_bulk_write(self) -> None:
        await self.collection.insert_one({})
        coll: AgnosticCollection = self.collection
        requests: List[InsertOne[Movie]] = [InsertOne(Movie(name="American Graffiti", year=1973))]
        result_one = await coll.bulk_write(requests)
        self.assertTrue(result_one.acknowledged)
        new_requests: List[Union[InsertOne[Movie], ReplaceOne[Movie]]] = []
        input_list: List[Union[InsertOne[Movie], ReplaceOne[Movie]]] = [
            InsertOne(Movie(name="American Graffiti", year=1973)),
            ReplaceOne({}, Movie(name="American Graffiti", year=1973)),
        ]
        for i in input_list:
            new_requests.append(i)
        result_two = await coll.bulk_write(new_requests)
        self.assertTrue(result_two.acknowledged)

    # Because ReplaceOne is not generic, type checking is not enforced for ReplaceOne in the first example.
    @only_type_check
    @asyncio_test
    async def test_bulk_write_heterogeneous(self):
        coll: AgnosticCollection = self.collection
        requests: List[Union[InsertOne[Movie], ReplaceOne, DeleteOne]] = [
            InsertOne(Movie(name="American Graffiti", year=1973)),
            ReplaceOne({}, {"name": "American Graffiti", "year": "WRONG_TYPE"}),
            DeleteOne({}),
        ]
        result_one = await coll.bulk_write(requests)
        self.assertTrue(result_one.acknowledged)
        requests_two: List[Union[InsertOne[Movie], ReplaceOne[Movie], DeleteOne]] = [
            InsertOne(Movie(name="American Graffiti", year=1973)),
            ReplaceOne(
                {},
                {"name": "American Graffiti", "year": "WRONG_TYPE"},
            ),
            DeleteOne({}),
        ]
        result_two = await coll.bulk_write(requests_two)
        self.assertTrue(result_two.acknowledged)

    @asyncio_test
    async def test_command(self) -> None:
        result: Dict = await self.cx.admin.command("ping")
        result.items()

    @asyncio_test
    async def test_list_collections(self) -> None:
        cursor = await self.cx.test.list_collections()
        value = await cursor.next()
        value.items()

    @asyncio_test
    async def test_list_databases(self) -> None:
        cursor = await self.cx.list_databases()
        value = await cursor.next()
        value.items()

    @asyncio_test
    async def test_default_document_type(self) -> None:
        client = self.asyncio_client()
        self.addCleanup(client.close)
        coll = client.test.test
        doc = {"my": "doc"}
        await coll.insert_one(doc)
        retrieved = await coll.find_one({"_id": doc["_id"]})
        assert retrieved is not None
        retrieved["a"] = 1

    @asyncio_test
    async def test_aggregate_pipeline(self) -> None:
        coll3 = self.cx.test.test3
        await coll3.insert_many(
            [
                {"x": 1, "tags": ["dog", "cat"]},
                {"x": 2, "tags": ["cat"]},
                {"x": 2, "tags": ["mouse", "cat", "dog"]},
                {"x": 3, "tags": []},
            ]
        )

        class mydict(Dict[str, Any]):
            pass

        result = coll3.aggregate(
            [
                mydict({"$unwind": "$tags"}),
                {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
                {"$sort": SON([("count", -1), ("_id", -1)])},
            ]
        )
        self.assertTrue(len([doc async for doc in result]))

    @asyncio_test
    async def test_with_transaction(self) -> None:
        async def execute_transaction(session):
            pass

        async with await self.cx.start_session() as session:
            return await session.with_transaction(
                execute_transaction, read_preference=ReadPreference.PRIMARY
            )


class TestDocumentType(AsyncIOTestCase):
    @only_type_check
    def test_typeddict_explicit_document_type(self) -> None:
        out = MovieWithId(_id=ObjectId(), name="THX-1138", year=1971)
        assert out is not None
        # This should fail because the output is a Movie.
        assert out["foo"]  # type:ignore[typeddict-item]
        assert out["_id"]

    # This should work the same as the test above, but this time using NotRequired to allow
    # automatic insertion of the _id field by insert_one.
    @only_type_check
    def test_typeddict_not_required_document_type(self) -> None:
        out = ImplicitMovie(name="THX-1138", year=1971)
        assert out is not None
        # This should fail because the output is a Movie.
        assert out["foo"]  # type:ignore[typeddict-item]
        # pyright gives reportTypedDictNotRequiredAccess for the following:
        assert out["_id"]

    @only_type_check
    def test_typeddict_empty_document_type(self) -> None:
        out = Movie(name="THX-1138", year=1971)
        assert out is not None
        # This should fail because the output is a Movie.
        assert out["foo"]  # type:ignore[typeddict-item]
        # This should fail because _id is not included in our TypedDict definition.
        assert out["_id"]  # type:ignore[typeddict-item]


class TestCommandDocumentType(AsyncIOTestCase):
    @only_type_check
    async def test_default(self) -> None:
        client: AgnosticClient = AgnosticClient()
        result: Dict = await client.admin.command("ping")
        result["a"] = 1

    @only_type_check
    async def test_explicit_document_type(self) -> None:
        client: AgnosticClient = AgnosticClient()
        codec_options: CodecOptions[Dict[str, Any]] = CodecOptions()
        result = await client.admin.command("ping", codec_options=codec_options)
        result["a"] = 1

    @only_type_check
    async def test_typeddict_document_type(self) -> None:
        client: AgnosticClient = AgnosticClient()
        codec_options: CodecOptions[Movie] = CodecOptions()
        result = await client.admin.command("ping", codec_options=codec_options)
        assert result["year"] == 1
        assert result["name"] == "a"

    @only_type_check
    async def test_raw_bson_document_type(self) -> None:
        client: AgnosticClient = AgnosticClient()
        codec_options = CodecOptions(RawBSONDocument)
        result: RawBSONDocument = await client.admin.command(
            "ping", codec_options=codec_options
        )  # Fix once @overload for command works
        assert len(result.raw) > 0

    @only_type_check
    async def test_son_document_type(self) -> None:
        client = AgnosticClient(document_class=SON[str, Any])
        codec_options = CodecOptions(SON[str, Any])
        result = await client.admin.command("ping", codec_options=codec_options)
        result["a"] = 1


if __name__ == "__main__":
    unittest.main()
