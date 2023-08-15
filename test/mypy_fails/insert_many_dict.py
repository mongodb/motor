import asyncio

from motor.core import AgnosticClient


async def _main():
    client: AgnosticClient = AgnosticClient()
    await client.test.test.insert_many(
        {"a": 1}
    )  # error: Dict entry 0 has incompatible type "str": "int"; expected "Mapping[str, Any]": "int"


loop = asyncio.get_event_loop()
loop.run_until_complete(_main())
loop.close()
