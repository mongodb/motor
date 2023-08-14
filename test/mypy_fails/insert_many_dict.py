import asyncio

from motor.core import AgnosticClient, AgnosticCollection


async def _main():
    client: AgnosticClient = AgnosticClient()
    coll: AgnosticCollection = client.test.test
    await coll.insert_many(
        {"a": 1}
    )  # error: Dict entry 0 has incompatible type "str": "int"; expected "Mapping[str, Any]": "int"


loop = asyncio.get_event_loop()
loop.run_until_complete(_main())
loop.close()
