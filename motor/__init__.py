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

"""Motor, an asynchronous driver for MongoDB."""

import warnings

version_tuple = (0, 3)

import pymongo


def get_version_string():
    if isinstance(version_tuple[-1], str):
        return '.'.join(str(v) for v in version_tuple[:-1]) + version_tuple[-1]
    return '.'.join(str(v) for v in version_tuple)

version = get_version_string()
"""Current version of Motor."""

expected_pymongo_version = '2.7.1'
if pymongo.version != expected_pymongo_version:
    msg = (
        "Motor %s requires PyMongo at exactly version %s. "
        "You have PyMongo %s."
    ) % (version, expected_pymongo_version, pymongo.version)

    raise ImportError(msg)

from . import core, motor_gridfs, motor_py3_compat, util
from .frameworks import tornado as tornado_framework
from .metaprogramming import create_class_with_framework
from .motor_common import callback_type_error

__all__ = ['MotorClient', 'MotorReplicaSetClient', 'Op']


MotorClient = create_class_with_framework(
    core.AgnosticClient,
    tornado_framework)


MotorReplicaSetClient = create_class_with_framework(
    core.AgnosticReplicaSetClient,
    tornado_framework)


MotorDatabase = create_class_with_framework(
    core.AgnosticDatabase,
    tornado_framework)


MotorCollection = create_class_with_framework(
    core.AgnosticCollection,
    tornado_framework)


MotorCursor = create_class_with_framework(
    core.AgnosticCursor,
    tornado_framework)


MotorCommandCursor = create_class_with_framework(
    core.AgnosticCommandCursor,
    tornado_framework)


MotorBulkOperationBuilder = create_class_with_framework(
    core.AgnosticBulkOperationBuilder,
    tornado_framework)


MotorGridFS = create_class_with_framework(
    motor_gridfs.AgnosticGridFS,
    tornado_framework)


MotorGridIn = create_class_with_framework(
    motor_gridfs.AgnosticGridIn,
    tornado_framework)


MotorGridOut = create_class_with_framework(
    motor_gridfs.AgnosticGridOut,
    tornado_framework)


MotorGridOutCursor = create_class_with_framework(
    motor_gridfs.AgnosticGridOutCursor,
    tornado_framework)


def Op(fn, *args, **kwargs):
    """Obsolete; here for backwards compatibility with Motor 0.1.

    Op had been necessary for ease-of-use with Tornado 2 and @gen.engine. But
    Motor 0.2 is built for Tornado 3, @gen.coroutine, and Futures, so motor.Op
    is deprecated.
    """
    msg = "motor.Op is deprecated, simply call %s and yield its Future." % (
        fn.__name__)

    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    result = fn(*args, **kwargs)
    assert tornado_framework.is_future(result)
    return result
