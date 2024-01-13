# Author: obnoxious, fuck mongodb for not implementing AnyIO and making me do this
# I fucking hate you.

# Seriously, like a lot.


"""Trio support for Motor, an asynchronous driver for MongoDB."""
from . import core, motor_gridfs
from .frameworks import trio as trio_framework
from .metaprogramming import T, create_class_with_framework

__all__ = [
    "TrioMotorClient",
    "TrioMotorClientSession",
    "TrioMotorDatabase",
    "TrioMotorCollection",
    "TrioMotorCursor",
    "TrioMotorCommandCursor",
    "TrioMotorChangeStream",
    "TrioMotorGridFSBucket",
    "TrioMotorGridIn",
    "TrioMotorGridOut",
    "TrioMotorGridOutCursor",
    "TrioMotorClientEncryption",
]


def create_trio_class(cls: T) -> T:
    return create_class_with_framework(
        cls=cls, framework=trio_framework, module_name="motor.motor_trio"
    )


TrioMotorClient = create_trio_class(core.AgnosticClient)


TrioMotorClientSession = create_trio_class(core.AgnosticClientSession)


TrioMotorDatabase = create_trio_class(core.AgnosticDatabase)


TrioMotorCollection = create_trio_class(core.AgnosticCollection)


TrioMotorCursor = create_trio_class(core.AgnosticCursor)


TrioMotorCommandCursor = create_trio_class(core.AgnosticCommandCursor)


TrioMotorLatentCommandCursor = create_trio_class(core.AgnosticLatentCommandCursor)


TrioMotorChangeStream = create_trio_class(core.AgnosticChangeStream)


TrioMotorGridFSBucket = create_trio_class(motor_gridfs.AgnosticGridFSBucket)


TrioMotorGridIn = create_trio_class(motor_gridfs.AgnosticGridIn)


TrioMotorGridOut = create_trio_class(motor_gridfs.AgnosticGridOut)


TrioMotorGridOutCursor = create_trio_class(motor_gridfs.AgnosticGridOutCursor)


TrioMotorClientEncryption = create_trio_class(core.AgnosticClientEncryption)
