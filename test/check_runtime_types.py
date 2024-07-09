from typing import Any, Dict

from motor.motor_asyncio import (
    AsyncIOMotorChangeStream,
    AsyncIOMotorClient,
    AsyncIOMotorClientEncryption,
    AsyncIOMotorCollection,
    AsyncIOMotorCursor,
    AsyncIOMotorDatabase,
)

client: AsyncIOMotorClient[Dict[str, Any]]
db: AsyncIOMotorDatabase[Dict[str, Any]]
cur: AsyncIOMotorCursor[Dict[str, Any]]
coll: AsyncIOMotorCollection[Dict[str, Any]]
cs: AsyncIOMotorChangeStream[Dict[str, Any]]
enc: AsyncIOMotorClientEncryption[Dict[str, Any]]
