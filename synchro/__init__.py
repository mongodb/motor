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
from tornado.ioloop import IOLoop

import motor
import motor.frameworks.tornado
import motor.motor_tornado
from motor.metaprogramming import MotorAttributeFactory

# Make e.g. "from pymongo.errors import AutoReconnect" work. Note that
# importing * won't pick up underscore-prefixed attrs.
from gridfs.errors import *
from pymongo import *
from pymongo import (operations,
                     server_selectors,
                     server_type,
                     son_manipulator,
                     ssl_match_hostname,
                     ssl_support,
                     write_concern)
from pymongo.auth import _build_credentials_tuple
from pymongo.helpers import _unpack_response, _check_command_response
from pymongo.common import *
from pymongo.cursor import *
from pymongo.cursor import _QUERY_OPTIONS
from pymongo.errors import *
from pymongo.message import (_COMMAND_OVERHEAD,
                             _CursorAddress,
                             _gen_find_command,
                             _maybe_add_read_preference)
from pymongo.monitor import *
from pymongo.monitoring import *
from pymongo.monitoring import _LISTENERS, _Listeners
from pymongo.operations import *
from pymongo.pool import *
from pymongo.periodic_executor import *
from pymongo.periodic_executor import _EXECUTORS
from pymongo.read_preferences import *
from pymongo.read_preferences import _ServerMode
from pymongo.results import *
from pymongo.results import _WriteResult
from pymongo.server import *
from pymongo.server_selectors import *
from pymongo.settings import *
from pymongo.ssl_support import *
from pymongo.son_manipulator import *
from pymongo.topology import *
from pymongo.topology_description import *
from pymongo.uri_parser import *
from pymongo.uri_parser import _partition, _rpartition
from pymongo.write_concern import *
from pymongo import auth
from pymongo.auth import *
from pymongo.auth import _password_digest
from gridfs.grid_file import DEFAULT_CHUNK_SIZE, _SEEK_CUR, _SEEK_END

from pymongo import GEOSPHERE, HASHED
from pymongo.pool import SocketInfo, Pool


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
            client = MongoClient(delegate=motor_obj.database.client)
            database = Database(client, motor_obj.database.name)
            return Collection(database, motor_obj.name, delegate=motor_obj)
        if isinstance(motor_obj, motor.MotorDatabase):
            client = MongoClient(delegate=motor_obj.client)
            return Database(client, motor_obj.name, delegate=motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorAggregationCursor):
            return CommandCursor(motor_obj)
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
    def __init__(self, name):
        self.name = name

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


def wrap_outgoing(delegate_attr):
    for decoration in ('is_motorcursor_chaining_method',
                       'is_wrap_method'):
        if getattr(delegate_attr, decoration, False):
            return True

    return False


class SynchroMeta(type):
    """This metaclass customizes creation of Synchro's MongoClient, Database,
    etc., classes:

    - All asynchronized methods of Motor classes, such as
      MotorDatabase.command(), are re-synchronized.

    - Properties delegated from Motor's classes to PyMongo's, such as ``name``
      or ``host``, are delegated **again** from Synchro's class to Motor's.

    - Motor methods which return Motor class instances are wrapped to return
      Synchro class instances.

    - Certain internals accessed by PyMongo's unittests, such as _Cursor__data,
      are delegated from Synchro directly to PyMongo.
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
                if attrname in attrs:
                    continue

                if getattr(delegate_attr, 'is_async_method', False):
                    # Re-synchronize the method.
                    setattr(new_class, attrname, Sync(attrname))
                elif wrap_outgoing(delegate_attr):
                    # Wrap MotorCursors in Synchro Cursors.
                    wrapper = WrapOutgoing()
                    wrapper.name = attrname
                    setattr(new_class, attrname, wrapper)
                elif isinstance(delegate_attr, property):
                    # Delegate the property from Synchro to Motor.
                    setattr(new_class, attrname, delegate_attr)

        # Set DelegateProperties' and SynchroProperties' names.
        for name, attr in attrs.items():
            if isinstance(attr, (MotorAttributeFactory,
                                 SynchroProperty,
                                 WrapOutgoing)):
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

    def synchronize(self, async_method):
        """
        @param async_method: Bound method of a MotorClient, MotorDatabase, etc.
        @return:             A synchronous wrapper around the method
        """
        @functools.wraps(async_method)
        def synchronized_method(*args, **kwargs):
            @functools.wraps(async_method)
            def partial():
                return async_method(*args, **kwargs)

            return IOLoop.current().run_sync(partial)
    
        return synchronized_method


class MongoClient(Synchro):
    __delegate_class__ = motor.MotorClient
    HOST = 'localhost'
    PORT = 27017

    _cache_credentials = SynchroProperty()
    get_database = WrapOutgoing()
    get_default_database = WrapOutgoing()
    max_pool_size = SynchroProperty()
    max_write_batch_size = SynchroProperty()

    def __init__(self, host=None, port=None, *args, **kwargs):
        # So that TestClient.test_constants and test_types work.
        host = host if host is not None else MongoClient.HOST
        port = port if port is not None else MongoClient.PORT

        self.delegate = kwargs.pop('delegate', None)

        # Motor passes connect=False by default.
        kwargs.setdefault('connect', True)
        if not self.delegate:
            self.delegate = self.__delegate_class__(host, port, *args, **kwargs)

    @property
    def is_locked(self):
        # MotorClient doesn't support the is_locked property.
        # Synchro has already synchronized current_op; use it.
        result = self.admin.current_op()
        return bool(result.get('fsyncLock', None))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.delegate.close()

    def __getattr__(self, name):
        return Database(self, name, delegate=getattr(self.delegate, name))

    def __getitem__(self, name):
        return Database(self, name, delegate=self.delegate[name])

    _MongoClient__options  = SynchroProperty()
    _get_topology          = SynchroProperty()
    _kill_cursors_executor = SynchroProperty()


class Database(Synchro):
    __delegate_class__ = motor.MotorDatabase
    get_collection     = WrapOutgoing()

    def __init__(self, client, name, delegate=None):
        assert isinstance(client, MongoClient), (
            "Expected MongoClient, got %s"
            % repr(client))

        self._client = client
        self.delegate = delegate or client.delegate[name]
        assert isinstance(self.delegate, motor.MotorDatabase), (
            "synchro.Database delegate must be MotorDatabase, not "
            " %s" % repr(self.delegate))

    def add_son_manipulator(self, manipulator):
        if isinstance(manipulator, son_manipulator.AutoReference):
            db = manipulator.database
            if isinstance(db, Database):
                manipulator.database = db.delegate.delegate

        self.delegate.add_son_manipulator(manipulator)

    @property
    def client(self):
        return self._client

    def __getattr__(self, name):
        return Collection(self, name, delegate=getattr(self.delegate, name))

    def __getitem__(self, name):
        return Collection(self, name, delegate=self.delegate[name])


class Collection(Synchro):
    __delegate_class__ = motor.MotorCollection

    find                            = WrapOutgoing()
    initialize_unordered_bulk_op    = WrapOutgoing()
    initialize_ordered_bulk_op      = WrapOutgoing()

    def __init__(self, database, name, delegate=None):
        if not isinstance(database, Database):
            raise TypeError(
                "First argument to synchro Collection must be synchro "
                "Database, not %s" % repr(database))

        self.database = database
        self.delegate = delegate or database.delegate[name]

        if not isinstance(self.delegate, motor.MotorCollection):
            raise TypeError(
                "Expected to get synchro Collection from Database,"
                " got %s" % repr(self.delegate))

    def aggregate(self, *args, **kwargs):
        # Motor does no I/O initially in aggregate() but PyMongo does.
        cursor = wrap_synchro(self.delegate.aggregate)(*args, **kwargs)
        self.synchronize(cursor.delegate._get_more)()
        return cursor

    def __getattr__(self, name):
        # Access to collections with dotted names, like db.test.mike
        fullname = self.name + '.' + name
        return Collection(self.database, fullname, getattr(self.delegate, name))

    def __getitem__(self, name):
        # Access to collections with dotted names, like db.test.mike
        fullname = self.name + '.' + name
        return Collection(self.database, fullname, self.delegate[name])


class Cursor(Synchro):
    __delegate_class__ = motor.motor_tornado.MotorCursor

    rewind = WrapOutgoing()
    clone  = WrapOutgoing()
    close  = Sync('close')

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
            self.synchronize(cursor._get_more)()
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

    # For PyMongo tests that access cursor internals.
    _Cursor__data              = SynchroProperty()
    _Cursor__exhaust           = SynchroProperty()
    _Cursor__max_await_time_ms = SynchroProperty()
    _Cursor__max_time_ms       = SynchroProperty()
    _Cursor__query_flags       = SynchroProperty()
    _Cursor__query_spec        = SynchroProperty()
    _Cursor__read_preference   = SynchroProperty()
    _Cursor__retrieved         = SynchroProperty()
    _Cursor__spec              = SynchroProperty()


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

    __next__ = next


class CursorManager(object):
    # Motor doesn't support cursor managers, just avoid ImportError.
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

    def __init__(self, database, collection='fs'):
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


class GridFSBucket(Synchro):
    __delegate_class__ = motor.MotorGridFSBucket

    def __init__(self, database, bucket_name='fs'):
        if not isinstance(database, Database):
            raise TypeError(
                "Expected Database, got %s" % repr(database))

        self.delegate = motor.MotorGridFSBucket(database.delegate, bucket_name)

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


class SynchroGridOutProperty(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype):
        obj.synchronize(obj.delegate.open)()
        return getattr(obj.delegate, self.name)


class GridOut(Synchro):
    __delegate_class__ = motor.MotorGridOut

    _id          = SynchroGridOutProperty('_id')
    aliases      = SynchroGridOutProperty('aliases')
    chunk_size   = SynchroGridOutProperty('chunk_size')
    close        = SynchroGridOutProperty('close')
    content_type = SynchroGridOutProperty('content_type')
    filename     = SynchroGridOutProperty('filename')
    length       = SynchroGridOutProperty('length')
    md5          = SynchroGridOutProperty('md5')
    metadata     = SynchroGridOutProperty('metadata')
    name         = SynchroGridOutProperty('name')
    upload_date  = SynchroGridOutProperty('upload_date')

    def __init__(
            self, root_collection, file_id=None, file_document=None,
            delegate=None):
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
