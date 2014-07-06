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

import functools
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

import pymongo.auth
import pymongo.common
import pymongo.database
import pymongo.errors
import pymongo.mongo_client
import pymongo.mongo_replica_set_client
import pymongo.son_manipulator

from . import motor_py3_compat, util
from .frameworks import tornado as tornado_framework
from .core import (AsyncCommand,
                   DelegateMethod,
                   MotorClientBase,
                   MotorReplicaSetMonitor,
                   ReadOnlyProperty)
from .motor_common import callback_type_error

__all__ = ['MotorClient', 'MotorReplicaSetClient', 'Op']


class MotorClient(MotorClientBase):
    __delegate_class__ = pymongo.mongo_client.MongoClient

    kill_cursors = AsyncCommand()
    fsync        = AsyncCommand()
    unlock       = AsyncCommand()
    nodes        = ReadOnlyProperty()
    host         = ReadOnlyProperty()
    port         = ReadOnlyProperty()

    _simple_command = AsyncCommand(attr_name='__simple_command')
    _socket         = AsyncCommand(attr_name='__socket')

    def __init__(self, *args, **kwargs):
        """Create a new connection to a single MongoDB instance at *host:port*.

        MotorClient takes the same constructor arguments as
        :class:`~pymongo.mongo_client.MongoClient`, as well as:

        :Parameters:
          - `io_loop` (optional): Special :class:`tornado.ioloop.IOLoop`
            instance to use instead of default
        """
        if 'io_loop' in kwargs:
            io_loop = kwargs.pop('io_loop')
        else:
            io_loop = tornado_framework.get_event_loop()

        event_class = functools.partial(util.MotorGreenletEvent, io_loop)
        kwargs['_event_class'] = event_class
        super(MotorClient, self).__init__(io_loop, *args, **kwargs)

    @tornado_framework.coroutine
    def open(self):
        """Connect to the server.

        Takes an optional callback, or returns a Future that resolves to
        ``self`` when opened. This is convenient for checking at program
        startup time whether you can connect.

        .. doctest::

          >>> client = MotorClient()
          >>> # run_sync() returns the open client.
          >>> IOLoop.current().run_sync(client.open)
          MotorClient(MongoClient('localhost', 27017))

        ``open`` raises a :exc:`~pymongo.errors.ConnectionFailure` if it
        cannot connect, but note that auth failures aren't revealed until
        you attempt an operation on the open client.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)

        .. versionchanged:: 0.2
           :class:`MotorClient` now opens itself on demand, calling ``open``
           explicitly is now optional.
        """
        yield self._ensure_connected()
        tornado_framework.return_value(self)

    def _get_member(self):
        # TODO: expose the PyMongo Member, or otherwise avoid this.
        return self.delegate._MongoClient__member

    def _get_pools(self):
        member = self._get_member()
        return [member.pool] if member else [None]

    def _get_primary_pool(self):
        return self._get_pools()[0]


class MotorReplicaSetClient(MotorClientBase):
    __delegate_class__ = pymongo.mongo_replica_set_client.MongoReplicaSetClient

    primary     = ReadOnlyProperty()
    secondaries = ReadOnlyProperty()
    arbiters    = ReadOnlyProperty()
    hosts       = ReadOnlyProperty()
    seeds       = DelegateMethod()
    close       = DelegateMethod()

    _simple_command = AsyncCommand(attr_name='__simple_command')
    _socket         = AsyncCommand(attr_name='__socket')

    def __init__(self, *args, **kwargs):
        """Create a new connection to a MongoDB replica set.

        MotorReplicaSetClient takes the same constructor arguments as
        :class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient`,
        as well as:

        :Parameters:
          - `io_loop` (optional): Special :class:`tornado.ioloop.IOLoop`
            instance to use instead of default
        """
        if 'io_loop' in kwargs:
            io_loop = kwargs.pop('io_loop')
        else:
            io_loop = tornado_framework.get_event_loop()

        kwargs['_monitor_class'] = functools.partial(
            MotorReplicaSetMonitor, io_loop)

        super(MotorReplicaSetClient, self).__init__(io_loop, *args, **kwargs)

    @tornado_framework.coroutine
    def open(self):
        """Connect to the server.

        Takes an optional callback, or returns a Future that resolves to
        ``self`` when opened. This is convenient for checking at program
        startup time whether you can connect.

        .. doctest::

          >>> client = MotorClient()
          >>> # run_sync() returns the open client.
          >>> IOLoop.current().run_sync(client.open)
          MotorClient(MongoClient('localhost', 27017))

        ``open`` raises a :exc:`~pymongo.errors.ConnectionFailure` if it
        cannot connect, but note that auth failures aren't revealed until
        you attempt an operation on the open client.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)

        .. versionchanged:: 0.2
           :class:`MotorReplicaSetClient` now opens itself on demand, calling
           ``open`` explicitly is now optional.
        """
        yield self._ensure_connected(True)
        primary = self._get_member()
        if not primary:
            raise pymongo.errors.AutoReconnect('no primary is available')
        tornado_framework.return_value(self)

    def _get_member(self):
        # TODO: expose the PyMongo RSC members, or otherwise avoid this.
        # This raises if the RSState's error is set.
        rs_state = self.delegate._MongoReplicaSetClient__get_rs_state()
        return rs_state.primary_member

    def _get_pools(self):
        rs_state = self._get_member()
        return [member.pool for member in rs_state._members]

    def _get_primary_pool(self):
        primary_member = self._get_member()
        return primary_member.pool if primary_member else None


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
