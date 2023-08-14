import asyncio

from bson.raw_bson import RawBSONDocument

from motor.core import AgnosticClient


async def _main():
    client = AgnosticClient(document_class=RawBSONDocument)
    coll = client.test.test
    doc = {"my": "doc"}
    await coll.insert_one(doc)
    retrieved = await coll.find_one({"_id": doc["_id"]})
    assert retrieved is not None
    assert len(retrieved.raw) > 0
    retrieved[
        "foo"
    ] = "bar"  # error: Unsupported target for indexed assignment ("RawBSONDocument")  [index]
    client.test.test.insert_one(
        [{}]
    )  # error: Argument 1 to "insert_one" of "Collection" has incompatible type "List[Dict[<nothing>, <nothing>]]"; expected "Mapping[str, Any]"


loop = asyncio.get_event_loop()
loop.run_until_complete(_main())
loop.close()
