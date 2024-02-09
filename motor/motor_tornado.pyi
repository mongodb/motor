import sys

if sys.version_info >= (3, 8):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias

from motor import core, motor_gridfs

MotorClient: TypeAlias = core.AgnosticClient

MotorClientSession: TypeAlias = core.AgnosticClientSession

MotorDatabase: TypeAlias = core.AgnosticDatabase

MotorCollection: TypeAlias = core.AgnosticCollection

MotorCursor: TypeAlias = core.AgnosticCursor

MotorCommandCursor: TypeAlias = core.AgnosticCommandCursor

MotorLatentCommandCursor: TypeAlias = core.AgnosticLatentCommandCursor

MotorChangeStream: TypeAlias = core.AgnosticChangeStream

MotorGridFSBucket: TypeAlias = motor_gridfs.AgnosticGridFSBucket

MotorGridIn: TypeAlias = motor_gridfs.AgnosticGridIn

MotorGridOut: TypeAlias = motor_gridfs.AgnosticGridOut

MotorGridOutCursor: TypeAlias = motor_gridfs.AgnosticGridOutCursor

MotorClientEncryption: TypeAlias = core.AgnosticClientEncryption
