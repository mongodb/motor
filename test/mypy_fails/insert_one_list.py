import asyncio

from motor.core import AgnosticClient


async def _main():
    client: AgnosticClient = AgnosticClient()
    client.test.test.insert_one(
        [{}]
    )  # error: Argument 1 to "insert_one" of "Collection" has incompatible type "List[Dict[<nothing>, <nothing>]]"; expected "Mapping[str, Any]"


loop = asyncio.get_event_loop()
loop.run_until_complete(_main())
loop.close()
