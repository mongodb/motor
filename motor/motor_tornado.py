# Copyright 2011-2015 MongoDB, Inc.
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

"""Tornado support for Motor, an asynchronous driver for MongoDB."""

from __future__ import unicode_literals, absolute_import

import warnings

from . import core, motor_gridfs
from .frameworks import tornado as tornado_framework
from .metaprogramming import create_class_with_framework

# See https://bugs.python.org/issue21720
__all__ = list(map(str, ['MotorClient', 'MotorReplicaSetClient', 'Op']))


def create_motor_class(cls):
    return create_class_with_framework(cls, tornado_framework, 'motor')


MotorClient = create_motor_class(core.AgnosticClient)


MotorReplicaSetClient = create_motor_class(core.AgnosticReplicaSetClient)


MotorDatabase = create_motor_class(core.AgnosticDatabase)


MotorCollection = create_motor_class(core.AgnosticCollection)


MotorCursor = create_motor_class(core.AgnosticCursor)


MotorCommandCursor = create_motor_class(core.AgnosticCommandCursor)


MotorAggregationCursor = create_motor_class(core.AgnosticAggregationCursor)


MotorBulkOperationBuilder = create_motor_class(core.AgnosticBulkOperationBuilder)


MotorGridFS = create_motor_class(motor_gridfs.AgnosticGridFS)


MotorGridIn = create_motor_class(motor_gridfs.AgnosticGridIn)


MotorGridOut = create_motor_class(motor_gridfs.AgnosticGridOut)


MotorGridOutCursor = create_motor_class(motor_gridfs.AgnosticGridOutCursor)


def Op(fn, *args, **kwargs):
    """Obsolete; here for backwards compatibility with Motor 0.1.

    Op had been necessary for ease-of-use with Tornado 2 and @gen.engine. But
    Motor 0.2 is built for Tornado 3, @gen.coroutine, and Futures, so motor.Op
    is deprecated.
    """
    msg = "motor.Op is deprecated, simply call %s and yield its Future." % (
        fn.__name__)

    warnings.warn(msg, DeprecationWarning, stacklevel=2)
    return fn(*args, **kwargs)
