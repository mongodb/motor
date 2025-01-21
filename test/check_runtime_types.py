from typing import Any

from motor.motor_asyncio import (
    AsyncIOMotorChangeStream,
    AsyncIOMotorClient,
    AsyncIOMotorClientEncryption,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
    AsyncIOMotorDatabase,
)

client: AsyncIOMotorClient[dict[str, Any]]
db: AsyncIOMotorDatabase[dict[str, Any]]
cur: AsyncIOMotorCursor[dict[str, Any]]
coll: AsyncIOMotorCollection[dict[str, Any]]
cs: AsyncIOMotorChangeStream[dict[str, Any]]
enc: AsyncIOMotorClientEncryption[dict[str, Any]]
