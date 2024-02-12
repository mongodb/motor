import sys

if sys.version_info >= (3, 8):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from motor import core, motor_gridfs

__all__: list[str] = [
    "AsyncIOMotorClient",
    "AsyncIOMotorClientSession",
    "AsyncIOMotorDatabase",
    "AsyncIOMotorCollection",
    "AsyncIOMotorCursor",
    "AsyncIOMotorCommandCursor",
    "AsyncIOMotorChangeStream",
    "AsyncIOMotorGridFSBucket",
    "AsyncIOMotorGridIn",
    "AsyncIOMotorGridOut",
    "AsyncIOMotorGridOutCursor",
    "AsyncIOMotorClientEncryption",
]

AsyncIOMotorClient: TypeAlias = core.AgnosticClient

AsyncIOMotorClientSession: TypeAlias = core.AgnosticClientSession

AsyncIOMotorDatabase: TypeAlias = core.AgnosticDatabase

AsyncIOMotorCollection: TypeAlias = core.AgnosticCollection

AsyncIOMotorCursor: TypeAlias = core.AgnosticCursor

AsyncIOMotorCommandCursor: TypeAlias = core.AgnosticCommandCursor

AsyncIOMotorLatentCommandCursor: TypeAlias = core.AgnosticLatentCommandCursor

AsyncIOMotorChangeStream: TypeAlias = core.AgnosticChangeStream

AsyncIOMotorGridFSBucket: TypeAlias = motor_gridfs.AgnosticGridFSBucket

AsyncIOMotorGridIn: TypeAlias = motor_gridfs.AgnosticGridIn

AsyncIOMotorGridOut: TypeAlias = motor_gridfs.AgnosticGridOut

AsyncIOMotorGridOutCursor: TypeAlias = motor_gridfs.AgnosticGridOutCursor

AsyncIOMotorClientEncryption: TypeAlias = core.AgnosticClientEncryption
