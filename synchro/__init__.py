# Copyright 2012-2014 MongoDB, Inc.
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

from __future__ import unicode_literals

"""Synchro, a fake synchronous PyMongo implementation built on top of Motor,
for the sole purpose of checking that Motor passes the same unittests as
PyMongo.

DO NOT USE THIS MODULE.
"""

import functools
import inspect
import os
import sys
import time
import traceback
from tornado.ioloop import IOLoop

import motor
import motor.frameworks.tornado
import motor.motor_tornado
from motor.metaprogramming import (
    MotorAttributeFactory,
    ReadOnlyPropertyDescriptor,
    Unwrap)

# Make e.g. "from pymongo.errors import AutoReconnect" work. Note that
# importing * won't pick up underscore-prefixed attrs.
from gridfs.errors import *
from pymongo import *
from pymongo import member
from pymongo import operations
from pymongo import son_manipulator
from pymongo import ssl_match_hostname
from pymongo import write_concern
from pymongo.helpers import _unpack_response, _check_command_response
from pymongo.common import *
from pymongo.cursor import *
from pymongo.cursor import _QUERY_OPTIONS
from pymongo.errors import *
from pymongo.member import PRIMARY, SECONDARY, OTHER
from pymongo.operations import *
from pymongo.read_preferences import *
from pymongo.son_manipulator import *
from pymongo.uri_parser import *
from pymongo.uri_parser import _partition, _rpartition
from pymongo.write_concern import *
from pymongo import auth
from pymongo.auth import *
from pymongo.auth import _password_digest
from gridfs.grid_file import DEFAULT_CHUNK_SIZE, _SEEK_CUR, _SEEK_END

GridFile = None
have_gevent = False

from pymongo import GEOSPHERE, HASHED
from pymongo.pool import NO_REQUEST, NO_SOCKET_YET, SocketInfo, Pool, _closed
from pymongo.mongo_replica_set_client import _partition_node, Member, Monitor


def unwrap_synchro(fn):
    """If first argument to decorated function is a Synchro object, pass the
    wrapped Motor object into the function.
    """
    @functools.wraps(fn)
    def _unwrap_synchro(*args, **kwargs):
        def _unwrap_obj(obj):
            if isinstance(obj, Synchro):
                return obj.delegate
            else:
                return obj

        args = [_unwrap_obj(arg) for arg in args]
        kwargs = dict([
            (key, _unwrap_obj(value)) for key, value in kwargs.items()])
        return fn(*args, **kwargs)
    return _unwrap_synchro


def wrap_synchro(fn):
    """If decorated Synchro function returns a Motor object, wrap in a Synchro
    object.
    """
    @functools.wraps(fn)
    def _wrap_synchro(*args, **kwargs):
        motor_obj = fn(*args, **kwargs)

        # Not all Motor classes appear here, only those we need to return
        # from methods like map_reduce() or create_collection()
        if isinstance(motor_obj, motor.MotorCollection):
            client = MongoClient(delegate=motor_obj.database.connection)
            database = Database(client, motor_obj.database.name)
            return Collection(database, motor_obj.name)
        if isinstance(motor_obj, motor.MotorDatabase):
            client = MongoClient(delegate=motor_obj.connection)
            return Database(client, motor_obj.name)
        if isinstance(motor_obj, motor.motor_tornado.MotorCommandCursor):
            return CommandCursor(motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorCursor):
            return Cursor(motor_obj)
        if isinstance(motor_obj, motor.MotorBulkOperationBuilder):
            return BulkOperationBuilder(motor_obj)
        if isinstance(motor_obj, motor.MotorGridFS):
            return GridFS(motor_obj)
        if isinstance(motor_obj, motor.MotorGridIn):
            return GridIn(None, delegate=motor_obj)
        if isinstance(motor_obj, motor.MotorGridOut):
            return GridOut(None, delegate=motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorGridOutCursor):
            return GridOutCursor(motor_obj)
        else:
            return motor_obj

    return _wrap_synchro


class Sync(object):
    def __init__(self, name, has_write_concern):
        self.name = name
        self.has_write_concern = has_write_concern

    def __get__(self, obj, objtype):
        async_method = getattr(obj.delegate, self.name)
        return wrap_synchro(unwrap_synchro(obj.synchronize(async_method)))


class WrapOutgoing(object):
    def __get__(self, obj, objtype):
        # self.name is set by SynchroMeta.
        name = self.name

        def synchro_method(*args, **kwargs):
            motor_method = getattr(obj.delegate, name)
            return wrap_synchro(motor_method)(*args, **kwargs)

        return synchro_method


class SynchroProperty(object):
    """Used to fake private properties like MongoClient.__member - don't use
    for real properties like write_concern or you'll mask missing features in
    Motor!
    """
    def __init__(self):
        self.name = None

    def __get__(self, obj, objtype):
        # self.name is set by SynchroMeta.
        return getattr(obj.delegate.delegate, self.name)

    def __set__(self, obj, val):
        # self.name is set by SynchroMeta.
        return setattr(obj.delegate.delegate, self.name, val)


class SynchroMeta(type):
    """This metaclass customizes creation of Synchro's MongoClient, Database,
    etc., classes:

    - All asynchronized methods of Motor classes, such as
      MotorDatabase.command(), are re-synchronized.

    - Properties delegated from Motor's classes to PyMongo's, such as ``name``
      or ``host``, are delegated **again** from Synchro's class to Motor's.

    - Motor methods which return Motor class instances are wrapped to return
      Synchro class instances.

    - Certain properties that are included only because PyMongo's unittests
      access them, such as _BaseObject__set_slave_okay, are simulated.
    """

    def __new__(cls, name, bases, attrs):
        # Create the class, e.g. the Synchro MongoClient or Database class.
        new_class = type.__new__(cls, name, bases, attrs)

        # delegate_class is a Motor class like MotorClient.
        delegate_class = new_class.__delegate_class__

        if delegate_class:
            delegated_attrs = {}

            for klass in reversed(inspect.getmro(delegate_class)):
                delegated_attrs.update(klass.__dict__)

            for attrname, delegate_attr in delegated_attrs.items():
                # If attrname is in attrs, it means Synchro has overridden
                # this attribute, e.g. Database.add_son_manipulator which is
                # special-cased. Ignore such attrs.
                if attrname not in attrs:
                    if getattr(
                            delegate_attr, 'is_async_method', False):
                        # Re-synchronize the method.
                        sync_method = Sync(
                            attrname, delegate_attr.has_write_concern)
                        setattr(new_class, attrname, sync_method)
                    elif isinstance(
                            delegate_attr, Unwrap):
                        # Re-synchronize the method.
                        sync_method = Sync(
                            attrname, delegate_attr.prop.has_write_concern)
                        setattr(new_class, attrname, sync_method)
                    elif getattr(
                            delegate_attr,
                            'is_motorcursor_chaining_method',
                            False):
                        # Wrap MotorCursors in Synchro Cursors.
                        wrapper = WrapOutgoing()
                        wrapper.name = attrname
                        setattr(new_class, attrname, wrapper)
                    elif isinstance(
                            delegate_attr,
                            ReadOnlyPropertyDescriptor):
                        # Delegate the property from Synchro to Motor.
                        setattr(new_class, attrname, delegate_attr)

        # Set DelegateProperties' and SynchroProperties' names.
        for name, attr in attrs.items():
            if isinstance(
                    attr,
                    (MotorAttributeFactory, SynchroProperty, WrapOutgoing)
            ):
                attr.name = name

        return new_class


class Synchro(object):
    """
    Wraps a MotorClient, MotorDatabase, MotorCollection, etc. and
    makes it act like the synchronous pymongo equivalent
    """
    __metaclass__ = SynchroMeta
    __delegate_class__ = None

    def __cmp__(self, other):
        return cmp(self.delegate, other.delegate)

    _BaseObject__set_slave_okay = SynchroProperty()
    _BaseObject__set_safe       = SynchroProperty()

    def synchronize(self, async_method):
        """
        @param async_method:        Bound method of a MotorClient,
                                    MotorDatabase, etc.
        @return:                    A synchronous wrapper around the method
        """
        @functools.wraps(async_method)
        def synchronized_method(*args, **kwargs):
            # Motor doesn't support 'safe'; simulate it.
            if 'safe' in kwargs:
                safe = kwargs.pop('safe')
                if not isinstance(safe, bool):
                    raise TypeError('%r not valid for "safe"' % safe)

                kwargs['w'] = 1 if safe else 0

            @functools.wraps(async_method)
            def partial():
                return async_method(*args, **kwargs)

            return IOLoop.current().run_sync(partial)
    
        return synchronized_method

    # Motor doesn't support these deprecated attrs, but PyMongo still tests
    # that its classes do.
    @property
    def safe(self):
        try:
            safe, opts = self.delegate.delegate._get_write_mode()
            return safe
        except (AttributeError, InvalidOperation):
            return True

    @safe.setter
    def safe(self, value):
        if value:
            # Set Motor object's write_concern. Safe by default with no 'w'.
            self.delegate.write_concern.pop('w', None)
        else:
            # Unsafe.
            self.delegate.write_concern['w'] = 0

    @property
    def slave_okay(self):
        motor_obj = self.delegate
        pymongo_obj = motor_obj.delegate

        pref = getattr(motor_obj, 'read_preference', ReadPreference.PRIMARY)
        slave_okay = getattr(pymongo_obj, 'slave_okay', False)

        return (pref != ReadPreference.PRIMARY) or slave_okay

    def __eq__(self, other):
        return self.delegate == other.delegate

    _get_write_mode       = SynchroProperty()
    get_lasterror_options = SynchroProperty()


class MongoClientBase(Synchro):
    _cache_credentials = SynchroProperty()
    get_default_database = WrapOutgoing()
    max_pool_size = SynchroProperty()
    max_write_batch_size = SynchroProperty()

    def __init__(self, *args, **kwargs):
        # Make a unittest happy.
        self.use_greenlets = False
        self.auto_start_request = False

        # Motor doesn't implement auto_start_request.
        kwargs.pop('auto_start_request', None)

        if 'read_preference' not in kwargs and (
                kwargs.get('tag_sets') not in (None, [], [{}])):
            # Make test_mongos_connection.TestMongosConnection pass.
            raise ConfigurationError()

        # Motor doesn't support deprecated options slave_okay and safe; but
        # PyMongo still does.
        if 'read_preference' not in kwargs and (
                'slaveok' in kwargs or 'slave_okay' in kwargs):

            secondary = kwargs.pop('slave_okay', kwargs.pop('slaveok', False))
            kwargs['read_preference'] = (
                ReadPreference.SECONDARY_PREFERRED if secondary
                else ReadPreference.PRIMARY)

        gle_opts = dict([
            (k, v) for k, v in kwargs.items()
            if k in SAFE_OPTIONS])

        if gle_opts and 'w' not in gle_opts:
            kwargs['w'] = 1

        if 'safe' in kwargs:
            safe = kwargs.pop('safe')
            if not safe:
                kwargs.setdefault('w', 0)

        self.delegate = kwargs.pop('delegate', None)

        if not self.delegate:
            self.delegate = self.__delegate_class__(*args, **kwargs)

            # In PyMongo 2.9 "connect" is added as a synonym.
            if kwargs.get('_connect', kwargs.get('connect', True)):
                self.synchro_connect()

    def synchro_connect(self):
        # Try to connect the MotorClient before continuing; raise
        # ConnectionFailure if it times out.
        try:
            self.synchronize(self.delegate.open)()
        except AutoReconnect as e:
            raise ConnectionFailure(str(e))

    def start_request(self):
        raise NotImplementedError()

    in_request = end_request = start_request

    @property
    def is_locked(self):
        # MotorClient doesn't support the is_locked property.
        # Synchro has already synchronized current_op; use it.
        result = self.admin.current_op()
        return bool(result.get('fsyncLock', None))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.delegate.disconnect()

    def __getattr__(self, name):
        # If this is like client.db, then wrap the outgoing object with
        # Synchro's Database.
        return Database(self, name)

    __getitem__ = __getattr__


class MongoClient(MongoClientBase):
    __delegate_class__ = motor.MotorClient

    HOST = 'localhost'
    PORT = 27017

    def __init__(self, host=None, port=None, *args, **kwargs):
        # So that TestClient.test_constants and test_types work.
        host = host if host is not None else self.HOST
        port = port if port is not None else self.PORT

        super(MongoClient, self).__init__(host, port, *args, **kwargs)

    _MongoClient__member                = SynchroProperty()
    _MongoClient__repl                  = SynchroProperty()
    _MongoClient__net_timeout           = SynchroProperty()
    _MongoClient__conn_timeout          = SynchroProperty()
    _MongoClient__wait_queue_timeout    = SynchroProperty()
    _MongoClient__wait_queue_multiple   = SynchroProperty()
    _MongoClient__socket_keepalive      = SynchroProperty()
    _MongoClient__use_ssl               = SynchroProperty()
    _MongoClient__ssl_keyfile           = SynchroProperty()
    _MongoClient__ssl_certfile          = SynchroProperty()
    _MongoClient__ssl_ca_certs          = SynchroProperty()

class MasterSlaveConnection(object):
    """Motor doesn't support master-slave connections, this is just here so
       Synchro can import pymongo.master_slave_connection without error
    """
    pass


class MongoReplicaSetClient(MongoClientBase):
    __delegate_class__ = motor.MotorReplicaSetClient

    get_default_database                        = WrapOutgoing()
    _MongoReplicaSetClient__writer              = SynchroProperty()
    _MongoReplicaSetClient__rs_state            = SynchroProperty()
    _MongoReplicaSetClient__schedule_refresh    = SynchroProperty()
    _MongoReplicaSetClient__net_timeout         = SynchroProperty()
    _MongoReplicaSetClient__conn_timeout        = SynchroProperty()
    _MongoReplicaSetClient__wait_queue_timeout  = SynchroProperty()
    _MongoReplicaSetClient__wait_queue_multiple = SynchroProperty()
    _MongoReplicaSetClient__socket_keepalive    = SynchroProperty()
    _MongoReplicaSetClient__name                = SynchroProperty()
    _MongoReplicaSetClient__use_ssl             = SynchroProperty()
    _MongoReplicaSetClient__ssl_keyfile         = SynchroProperty()
    _MongoReplicaSetClient__ssl_certfile        = SynchroProperty()
    _MongoReplicaSetClient__ssl_ca_certs        = SynchroProperty()


class Database(Synchro):
    __delegate_class__ = motor.MotorDatabase

    def __init__(self, client, name):
        assert isinstance(client, (MongoClient, MongoReplicaSetClient)), (
            "Expected MongoClient or MongoReplicaSetClient, got %s"
            % repr(client))

        # "client" is modern, "connection" is deprecated.
        self.client = self.connection = client

        self.delegate = client.delegate[name]
        assert isinstance(self.delegate, motor.MotorDatabase), (
            "synchro.Database delegate must be MotorDatabase, not "
            " %s" % repr(self.delegate))

    def add_son_manipulator(self, manipulator):
        if isinstance(manipulator, son_manipulator.AutoReference):
            db = manipulator.database
            if isinstance(db, Database):
                manipulator.database = db.delegate.delegate

        self.delegate.add_son_manipulator(manipulator)

    def __getattr__(self, name):
        return Collection(self, name)

    __getitem__ = __getattr__


class Collection(Synchro):
    __delegate_class__ = motor.MotorCollection

    find                            = WrapOutgoing()
    initialize_unordered_bulk_op    = WrapOutgoing()
    initialize_ordered_bulk_op      = WrapOutgoing()

    def __init__(self, database, name):
        if not isinstance(database, Database):
            raise TypeError(
                "First argument to synchro Collection must be synchro "
                "Database, not %s" % repr(database))

        self.database = database
        self.delegate = database.delegate[name]

        if not isinstance(self.delegate, motor.MotorCollection):
            raise TypeError(
                "Expected to get synchro Collection from Database,"
                " got %s" % repr(self.delegate))

    def __getattr__(self, name):
        # Access to collections with dotted names, like db.test.mike
        return Collection(self.database, self.name + '.' + name)

    __getitem__ = __getattr__


class Cursor(Synchro):
    __delegate_class__ = motor.motor_tornado.MotorCursor

    rewind                     = WrapOutgoing()
    clone                      = WrapOutgoing()
    close                      = Sync('close', False)

    def __init__(self, motor_cursor):
        self.delegate = motor_cursor

    def __iter__(self):
        return self

    # These are special cases, they need to be accessed on the class, not just
    # on instances.
    @wrap_synchro
    def __copy__(self):
        return self.delegate.__copy__()

    @wrap_synchro
    def __deepcopy__(self, memo):
        return self.delegate.__deepcopy__(memo)

    def next(self):
        cursor = self.delegate

        if cursor._buffer_size():
            return cursor.next_object()
        elif cursor.alive:
            self.synchronize(cursor._refresh)()
            if cursor._buffer_size():
                return cursor.next_object()

        raise StopIteration

    def __getitem__(self, index):
        if isinstance(index, slice):
            return Cursor(self.delegate[index])
        else:
            to_list = self.synchronize(self.delegate[index].to_list)
            return to_list(length=10000)[0]

    @property
    @wrap_synchro
    def collection(self):
        return self.delegate.collection

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

        # Don't suppress exceptions.
        return False

    @property
    def _Cursor__slave_okay(self):
        # Another hack; PyMongo's tests don't check this field on
        # CommandCursor, so assume self.delegate is a regular Cursor.
        pymongo_cursor = self.delegate.delegate
        pref = pymongo_cursor._Cursor__read_preference
        return (
            pymongo_cursor._Cursor__slave_okay
            or pref != ReadPreference.PRIMARY)

    _Cursor__id                = SynchroProperty()
    _Cursor__query_options     = SynchroProperty()
    _Cursor__query_spec        = SynchroProperty()
    _Cursor__retrieved         = SynchroProperty()
    _Cursor__skip              = SynchroProperty()
    _Cursor__limit             = SynchroProperty()
    _Cursor__timeout           = SynchroProperty()
    _Cursor__snapshot          = SynchroProperty()
    _Cursor__tailable          = SynchroProperty()
    _Cursor__as_class          = SynchroProperty()
    _Cursor__await_data        = SynchroProperty()
    _Cursor__partial           = SynchroProperty()
    _Cursor__manipulate        = SynchroProperty()
    _Cursor__query_flags       = SynchroProperty()
    _Cursor__connection_id     = SynchroProperty()
    _Cursor__read_preference   = SynchroProperty()
    _Cursor__tag_sets          = SynchroProperty()
    _Cursor__fields            = SynchroProperty()
    _Cursor__spec              = SynchroProperty()
    _Cursor__hint              = SynchroProperty()
    _Cursor__exhaust           = SynchroProperty()
    _Cursor__compile_re        = SynchroProperty()
    _Cursor__max_time_ms       = SynchroProperty()
    _Cursor__comment           = SynchroProperty()
    _Cursor__min               = SynchroProperty()
    _Cursor__max               = SynchroProperty()
    _Cursor__secondary_acceptable_latency_ms = SynchroProperty()


class CommandCursor(Cursor):
    __delegate_class__ = motor.motor_tornado.MotorCommandCursor


class GridOutCursor(Cursor):
    __delegate_class__ = motor.motor_tornado.MotorGridOutCursor

    def __init__(self, delegate):
        if not isinstance(delegate, motor.motor_tornado.MotorGridOutCursor):
            raise TypeError(
                "Expected MotorGridOutCursor, got %r" % delegate)

        self.delegate = delegate

    def next(self):
        motor_grid_out = super(GridOutCursor, self).next()
        if motor_grid_out:
            return GridOut(self.collection, delegate=motor_grid_out)

    _Cursor__secondary_acceptable_latency_ms = SynchroProperty()


class CursorManager(object):
    """Motor doesn't support cursor managers, just avoid ImportError.
    """
    pass


class BulkOperationBuilder(Synchro):
    __delegate_class__ = motor.MotorBulkOperationBuilder

    def __init__(self, motor_bob):
        if not isinstance(motor_bob, motor.MotorBulkOperationBuilder):
            raise TypeError(
                "Expected MotorBulkOperationBuilder, got %r" % motor_bob)

        self.delegate = motor_bob


class GridFS(Synchro):
    __delegate_class__ = motor.MotorGridFS

    def __init__(self, database, collection='fs', _connect=True):
        if not isinstance(database, Database):
            raise TypeError(
                "Expected Database, got %s" % repr(database))

        self.delegate = motor.MotorGridFS(database.delegate, collection)

    def put(self, *args, **kwargs):
        return self.synchronize(self.delegate.put)(*args, **kwargs)

    def find(self, *args, **kwargs):
        motor_method = self.delegate.find
        unwrapping_method = wrap_synchro(unwrap_synchro(motor_method))
        return unwrapping_method(*args, **kwargs)


class GridIn(Synchro):
    __delegate_class__ = motor.MotorGridIn

    def __init__(self, collection, **kwargs):
        """Can be created with collection and kwargs like a PyMongo GridIn,
        or with a 'delegate' keyword arg, where delegate is a MotorGridIn.
        """
        delegate = kwargs.pop('delegate', None)
        if delegate:
            self.delegate = delegate
        else:
            if not isinstance(collection, Collection):
                raise TypeError(
                    "Expected Collection, got %s" % repr(collection))

            self.delegate = motor.MotorGridIn(collection.delegate, **kwargs)

    def __getattr__(self, item):
        return getattr(self.delegate, item)


class GridOut(Synchro):
    __delegate_class__ = motor.MotorGridOut

    def __init__(
            self, root_collection, file_id=None, file_document=None,
            _connect=True, delegate=None):
        """Can be created with collection and kwargs like a PyMongo GridOut,
        or with a 'delegate' keyword arg, where delegate is a MotorGridOut.
        """
        if delegate:
            self.delegate = delegate
        else:
            if not isinstance(root_collection, Collection):
                raise TypeError(
                    "Expected Collection, got %s" % repr(root_collection))

            self.delegate = motor.MotorGridOut(
                root_collection.delegate, file_id, file_document)

            if _connect:
                self.synchronize(self.delegate.open)()

    def __getattr__(self, item):
        self.synchronize(self.delegate.open)()
        return getattr(self.delegate, item)

    def __setattr__(self, key, value):
        # PyMongo's GridOut prohibits setting these values; do the same
        # to make PyMongo's assertRaises tests pass.
        if key in (
                "_id", "name", "content_type", "length", "chunk_size",
                "upload_date", "aliases", "metadata", "md5"):
            raise AttributeError()

        super(GridOut, self).__setattr__(key, value)


class TimeModule(object):
    """Fake time module so time.sleep() lets other tasks run on the IOLoop.

    See e.g. test_schedule_refresh() in test_replica_set_client.py.
    """
    def __getattr__(self, item):
        def sleep(seconds):
            loop = IOLoop.current()
            loop.add_timeout(time.time() + seconds, loop.stop)
            loop.start()

        if item == 'sleep':
            return sleep
        else:
            return getattr(time, item)
