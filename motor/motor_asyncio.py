# Copyright 2011-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals, absolute_import

"""Asyncio support for Motor, an asynchronous driver for MongoDB."""

__all__ = ['AsyncIOMotorClient', 'AsyncIOMotorReplicaSetClient']

from . import core, motor_gridfs
from .frameworks import asyncio as asyncio_framework
from .metaprogramming import create_class_with_framework


AsyncIOMotorClient = create_class_with_framework(
    core.AgnosticClient,
    asyncio_framework)


AsyncIOMotorReplicaSetClient = create_class_with_framework(
    core.AgnosticReplicaSetClient,
    asyncio_framework)


AsyncIOMotorDatabase = create_class_with_framework(
    core.AgnosticDatabase,
    asyncio_framework)


AsyncIOMotorCollection = create_class_with_framework(
    core.AgnosticCollection,
    asyncio_framework)


AsyncIOMotorCursor = create_class_with_framework(
    core.AgnosticCursor,
    asyncio_framework)


AsyncIOMotorCommandCursor = create_class_with_framework(
    core.AgnosticCommandCursor,
    asyncio_framework)


AsyncIOMotorBulkOperationBuilder = create_class_with_framework(
    core.AgnosticBulkOperationBuilder,
    asyncio_framework)


AsyncIOMotorGridFS = create_class_with_framework(
    motor_gridfs.AgnosticGridFS,
    asyncio_framework)


AsyncIOMotorGridIn = create_class_with_framework(
    motor_gridfs.AgnosticGridIn,
    asyncio_framework)


AsyncIOMotorGridOut = create_class_with_framework(
    motor_gridfs.AgnosticGridOut,
    asyncio_framework)


AsyncIOMotorGridOutCursor = create_class_with_framework(
    motor_gridfs.AgnosticGridOutCursor,
    asyncio_framework)
