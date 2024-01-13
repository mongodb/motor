import asyncio

from motor.motor_asyncio import AsyncIOMotorClient


async def main():
    client = AsyncIOMotorClient()

    db = client["database"]
    collection = db["collection"]

    await collection.insert_one({"test": "test"})


asyncio.run(main())
