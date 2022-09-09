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

"""Synchro, a fake synchronous PyMongo implementation built on top of Motor,
for the sole purpose of checking that Motor passes the same unittests as
PyMongo.

DO NOT USE THIS MODULE.
"""

import functools
import inspect
import unittest

# Make e.g. "from pymongo.errors import AutoReconnect" work. Note that
# importing * won't pick up underscore-prefixed attrs.
from gridfs import *
from gridfs import _disallow_transactions
from gridfs.errors import *
from gridfs.grid_file import (
    _SEEK_CUR,
    _SEEK_END,
    DEFAULT_CHUNK_SIZE,
    _clear_entity_type_registry,
)

# Work around circular imports.
from pymongo import *
from pymongo import (
    GEOSPHERE,
    HASHED,
    auth,
    change_stream,
    collation,
    compression_support,
    encryption_options,
    errors,
    event_loggers,
    message,
    operations,
    read_preferences,
    saslprep,
    server_selectors,
    server_type,
    ssl_support,
    write_concern,
)

# Added for API compat with pymongo.
try:
    from pymongo import _csot
except ImportError:
    pass
from pymongo.auth import *
from pymongo.auth import _build_credentials_tuple, _password_digest
from pymongo.client_session import TransactionOptions, _TxnState
from pymongo.collation import *
from pymongo.common import *
from pymongo.common import _MAX_END_SESSIONS, _UUID_REPRESENTATIONS
from pymongo.compression_support import _HAVE_SNAPPY, _HAVE_ZLIB, _HAVE_ZSTD
from pymongo.cursor import *
from pymongo.cursor import _QUERY_OPTIONS
from pymongo.encryption import *
from pymongo.encryption import _MONGOCRYPTD_TIMEOUT_MS, _Encrypter
from pymongo.encryption_options import *
from pymongo.encryption_options import _HAVE_PYMONGOCRYPT
from pymongo.errors import *
from pymongo.event_loggers import *
from pymongo.helpers import _check_command_response
from pymongo.lock import _create_lock
from pymongo.message import (
    _COMMAND_OVERHEAD,
    _CursorAddress,
    _gen_find_command,
    _maybe_add_read_preference,
)
from pymongo.monitor import *
from pymongo.monitoring import *
from pymongo.monitoring import _LISTENERS, _SENSITIVE_COMMANDS, _Listeners
from pymongo.ocsp_cache import _OCSPCache
from pymongo.operations import *
from pymongo.periodic_executor import *
from pymongo.periodic_executor import _EXECUTORS
from pymongo.pool import *
from pymongo.pool import _METADATA, Pool, SocketInfo, _PoolClosedError
from pymongo.read_concern import *
from pymongo.read_preferences import *
from pymongo.read_preferences import _ServerMode
from pymongo.results import *
from pymongo.results import _WriteResult
from pymongo.saslprep import *
from pymongo.server import *
from pymongo.server_selectors import *
from pymongo.settings import *
from pymongo.ssl_support import *
from pymongo.topology import *
from pymongo.topology_description import *
from pymongo.uri_parser import *
from pymongo.uri_parser import _HAVE_DNSPYTHON
from pymongo.write_concern import *
from tornado.ioloop import IOLoop

import motor
import motor.frameworks.tornado
import motor.motor_tornado

# Internal classes not declared in motor_tornado.py: retrieve from class cache.
from motor.core import AgnosticRawBatchCommandCursor as _AgnosticRawBatchCommandCursor
from motor.core import AgnosticRawBatchCursor as _AgnosticRawBatchCursor
from motor.core import _MotorTransactionContext
from motor.metaprogramming import MotorAttributeFactory
from motor.motor_tornado import create_motor_class

_MotorRawBatchCursor = create_motor_class(_AgnosticRawBatchCursor)
_MotorRawBatchCommandCursor = create_motor_class(_AgnosticRawBatchCommandCursor)


def wrap_synchro(fn):
    """If decorated Synchro function returns a Motor object, wrap in a Synchro
    object.
    """

    @functools.wraps(fn)
    def _wrap_synchro(*args, **kwargs):
        motor_obj = fn(*args, **kwargs)

        # Not all Motor classes appear here, only those we need to return
        # from methods like create_collection()
        if isinstance(motor_obj, motor.MotorCollection):
            client = MongoClient(delegate=motor_obj.database.client)
            database = Database(client, motor_obj.database.name)
            return Collection(database, motor_obj.name, delegate=motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorClientSession):
            return ClientSession(delegate=motor_obj)
        if isinstance(motor_obj, _MotorTransactionContext):
            return _SynchroTransactionContext(motor_obj)
        if isinstance(motor_obj, motor.MotorDatabase):
            client = MongoClient(delegate=motor_obj.client)
            return Database(client, motor_obj.name, delegate=motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorChangeStream):
            # Send the initial aggregate as PyMongo expects.
            motor_obj._lazy_init()
            return ChangeStream(motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorLatentCommandCursor):
            synchro_cursor = CommandCursor(motor_obj)
            # Send the initial command as PyMongo expects.
            if not motor_obj.started:
                synchro_cursor.synchronize(motor_obj._get_more)()
            return synchro_cursor
        if isinstance(motor_obj, motor.motor_tornado.MotorCommandCursor):
            return CommandCursor(motor_obj)
        if isinstance(motor_obj, _MotorRawBatchCommandCursor):
            return CommandCursor(motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorCursor):
            return Cursor(motor_obj)
        if isinstance(motor_obj, _MotorRawBatchCursor):
            return Cursor(motor_obj)
        if isinstance(motor_obj, motor.MotorGridIn):
            return GridIn(None, delegate=motor_obj)
        if isinstance(motor_obj, motor.MotorGridOut):
            return GridOut(None, delegate=motor_obj)
        if isinstance(motor_obj, motor.motor_tornado.MotorGridOutCursor):
            return GridOutCursor(motor_obj)
        else:
            return motor_obj

    return _wrap_synchro


def unwrap_synchro(fn):
    """Unwrap Synchro objects passed to a method and pass Motor objects instead."""

    @functools.wraps(fn)
    def _unwrap_synchro(*args, **kwargs):
        def _unwrap_obj(obj):
            if isinstance(obj, Synchro):
                return obj.delegate
            else:
                return obj

        args = [_unwrap_obj(arg) for arg in args]
        kwargs = dict([(key, _unwrap_obj(value)) for key, value in kwargs.items()])
        return fn(*args, **kwargs)

    return _unwrap_synchro


class SynchroAttr(object):
    # Name can be set by SynchroMeta if Sync() is used directly in class defn.
    def __init__(self, name=None):
        self.name = name


class Sync(SynchroAttr):
    def __get__(self, obj, objtype):
        async_method = getattr(obj.delegate, self.name)
        return wrap_synchro(unwrap_synchro(obj.synchronize(async_method)))


class WrapOutgoing(SynchroAttr):
    def __get__(self, obj, objtype):
        # self.name is set by SynchroMeta.
        name = self.name

        def synchro_method(*args, **kwargs):
            motor_method = getattr(obj.delegate, name)
            return wrap_synchro(unwrap_synchro(motor_method))(*args, **kwargs)

        return synchro_method


class SynchroProperty(SynchroAttr):
    """Used to fake private properties like MongoClient.__member - don't use
    for real properties like write_concern or you'll mask missing features in
    Motor!
    """

    def __get__(self, obj, objtype):
        # self.name is set by SynchroMeta.
        return getattr(obj.delegate.delegate, self.name)

    def __set__(self, obj, val):
        # self.name is set by SynchroMeta.
        return setattr(obj.delegate.delegate, self.name, val)


def wrap_outgoing(delegate_attr):
    for decoration in ("is_motorcursor_chaining_method", "is_wrap_method"):
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
                # this attribute, e.g. Collection.aggregate which is
                # special-cased. Ignore such attrs.
                if attrname in attrs:
                    continue

                if getattr(delegate_attr, "is_async_method", False):
                    # Re-synchronize the method.
                    setattr(new_class, attrname, Sync(attrname))
                elif wrap_outgoing(delegate_attr):
                    # Wrap Motor objects in Synchro objects.
                    wrapper = WrapOutgoing()
                    wrapper.name = attrname
                    setattr(new_class, attrname, wrapper)
                elif isinstance(delegate_attr, property):
                    # Delegate the property from Synchro to Motor.
                    setattr(new_class, attrname, delegate_attr)

        # Set DelegateProperties' and SynchroProperties' names.
        for name, attr in attrs.items():
            if isinstance(attr, (MotorAttributeFactory, SynchroAttr)):
                if attr.name is None:
                    attr.name = name

        return new_class


class Synchro(metaclass=SynchroMeta):
    """
    Wraps a MotorClient, MotorDatabase, MotorCollection, etc. and
    makes it act like the synchronous pymongo equivalent
    """

    __delegate_class__ = None

    def __eq__(self, other):
        if (
            isinstance(other, self.__class__)
            and hasattr(self, "delegate")
            and hasattr(other, "delegate")
        ):
            return self.delegate == other.delegate
        return NotImplemented

    def __hash__(self):
        return self.delegate.__hash__()

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
    HOST = "localhost"
    PORT = 27017

    get_database = WrapOutgoing()
    max_pool_size = SynchroProperty()
    start_session = Sync()
    watch = WrapOutgoing()
    __iter__ = None  # PYTHON-3084
    __next__ = Sync()

    def __init__(self, host=None, port=None, *args, **kwargs):
        # So that TestClient.test_constants and test_types work.
        host = host if host is not None else MongoClient.HOST
        port = port if port is not None else MongoClient.PORT

        self.delegate = kwargs.pop("delegate", None)

        # Motor passes connect=False by default.
        kwargs.setdefault("connect", True)
        if not self.delegate:
            self.delegate = self.__delegate_class__(host, port, *args, **kwargs)

    # PyMongo expects this to return a real MongoClient, unwrap it.
    def _duplicate(self, **kwargs):
        client = self.delegate._duplicate(**kwargs)
        if isinstance(client, Synchro):
            return client.delegate.delegate
        return client

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.delegate.close()

    def __getattr__(self, name):
        return Database(self, name, delegate=getattr(self.delegate, name))

    def __getitem__(self, name):
        return Database(self, name, delegate=self.delegate[name])

    # For PyMongo tests that access client internals.
    _MongoClient__all_credentials = SynchroProperty()
    _MongoClient__kill_cursors_queue = SynchroProperty()
    _MongoClient__options = SynchroProperty()
    _cache_credentials = SynchroProperty()
    _close_cursor_now = SynchroProperty()
    _get_topology = SynchroProperty()
    _topology = SynchroProperty()
    _kill_cursors_executor = SynchroProperty()
    _topology_settings = SynchroProperty()
    _process_periodic_tasks = SynchroProperty()


class _SynchroTransactionContext(Synchro):
    def __init__(self, delegate):
        self.delegate = delegate

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        motor_session = self.delegate._session
        if motor_session.in_transaction:
            if exc_val is None:
                self.synchronize(motor_session.commit_transaction)()
            else:
                self.synchronize(motor_session.abort_transaction)()


class ClientSession(Synchro):
    __delegate_class__ = motor.motor_tornado.MotorClientSession

    start_transaction = WrapOutgoing()
    client = SynchroProperty()

    def __init__(self, delegate):
        self.delegate = delegate

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.synchronize(self.delegate.end_session)

    def with_transaction(self, *args, **kwargs):
        raise unittest.SkipTest("MOTOR-606 Synchro does not support with_transaction")

    # For PyMongo tests that access session internals.
    _client = SynchroProperty()
    _pinned_address = SynchroProperty()
    _server_session = SynchroProperty()
    _transaction = SynchroProperty()
    _transaction_id = SynchroProperty()
    _txn_read_preference = SynchroProperty()


class Database(Synchro):
    __delegate_class__ = motor.MotorDatabase

    get_collection = WrapOutgoing()
    watch = WrapOutgoing()
    aggregate = WrapOutgoing()
    __bool__ = Sync()

    def __init__(self, client, name, **kwargs):
        assert isinstance(client, MongoClient), "Expected MongoClient, got %s" % repr(client)

        self._client = client
        self.delegate = kwargs.get("delegate")
        if self.delegate is None:
            self.delegate = motor.MotorDatabase(client.delegate, name, **kwargs)

        assert isinstance(
            self.delegate, motor.MotorDatabase
        ), "synchro.Database delegate must be MotorDatabase, not %s" % repr(self.delegate)

    @property
    def client(self):
        return self._client

    def __getattr__(self, name):
        return Collection(self, name, delegate=getattr(self.delegate, name))

    def __getitem__(self, name):
        return Collection(self, name, delegate=self.delegate[name])


class Collection(Synchro):
    __delegate_class__ = motor.MotorCollection

    find = WrapOutgoing()
    find_raw_batches = WrapOutgoing()
    aggregate = WrapOutgoing()
    aggregate_raw_batches = WrapOutgoing()
    list_indexes = WrapOutgoing()
    watch = WrapOutgoing()
    __bool__ = WrapOutgoing()

    def __init__(self, database, name, **kwargs):
        if not isinstance(database, Database):
            raise TypeError(
                "First argument to synchro Collection must be synchro "
                "Database, not %s" % repr(database)
            )

        self.database = database
        self.delegate = kwargs.get("delegate")
        if self.delegate is None:
            self.delegate = motor.MotorCollection(self.database.delegate, name, **kwargs)

        if not isinstance(self.delegate, motor.MotorCollection):
            raise TypeError(
                "Expected to get synchro Collection from Database got %s" % repr(self.delegate)
            )

    def __getattr__(self, name):
        # Access to collections with dotted names, like db.test.mike
        fullname = self.name + "." + name
        return Collection(self.database, fullname, delegate=getattr(self.delegate, name))

    def __getitem__(self, name):
        # Access to collections with dotted names, like db.test['mike']
        fullname = self.name + "." + name
        return Collection(self.database, fullname, delegate=self.delegate[name])


class ChangeStream(Synchro):
    __delegate_class__ = motor.motor_tornado.MotorChangeStream

    _next = Sync("next")
    try_next = Sync("try_next")
    close = Sync("close")

    def next(self):
        try:
            return self._next()
        except StopAsyncIteration:
            raise StopIteration

    def __init__(self, motor_change_stream):
        self.delegate = motor_change_stream

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __iter__(self):
        return self

    __next__ = next

    # For PyMongo tests that access change stream internals.

    @property
    def _cursor(self):
        raise unittest.SkipTest("test accesses internal _cursor field")

    _batch_size = SynchroProperty()
    _client = SynchroProperty()
    _full_document = SynchroProperty()
    _max_await_time_ms = SynchroProperty()
    _pipeline = SynchroProperty()
    _target = SynchroProperty()


class Cursor(Synchro):
    __delegate_class__ = motor.motor_tornado.MotorCursor

    batch_size = WrapOutgoing()
    rewind = WrapOutgoing()
    clone = WrapOutgoing()
    close = Sync("close")

    _next = Sync("next")

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
        try:
            return self._next()
        except StopAsyncIteration:
            raise StopIteration

    __next__ = next

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
    _Cursor__data = SynchroProperty()
    _Cursor__exhaust = SynchroProperty()
    _Cursor__max_await_time_ms = SynchroProperty()
    _Cursor__max_time_ms = SynchroProperty()
    _Cursor__query_flags = SynchroProperty()
    _Cursor__query_spec = SynchroProperty()
    _Cursor__retrieved = SynchroProperty()
    _Cursor__spec = SynchroProperty()
    _read_preference = SynchroProperty()


class CommandCursor(Cursor):
    __delegate_class__ = motor.motor_tornado.MotorCommandCursor


class GridOutCursor(Cursor):
    __delegate_class__ = motor.motor_tornado.MotorGridOutCursor

    def __init__(self, delegate):
        if not isinstance(delegate, motor.motor_tornado.MotorGridOutCursor):
            raise TypeError("Expected MotorGridOutCursor, got %r" % delegate)

        super().__init__(delegate)

    def next(self):
        motor_grid_out = super().next()
        if motor_grid_out:
            return GridOut(self.collection, delegate=motor_grid_out)

    __next__ = next


class CursorManager(object):
    # Motor doesn't support cursor managers, just avoid ImportError.
    pass


class BulkOperationBuilder(object):
    pass


class GridFSBucket(Synchro):
    __delegate_class__ = motor.MotorGridFSBucket

    find = WrapOutgoing()

    def __init__(self, database, *args, **kwargs):
        if not isinstance(database, Database):
            raise TypeError("Expected Database, got %s" % repr(database))

        self.delegate = motor.MotorGridFSBucket(database.delegate, *args, **kwargs)


class GridIn(Synchro):
    __delegate_class__ = motor.MotorGridIn
    _chunk_number = SynchroProperty()
    _closed = SynchroProperty()

    def __init__(self, collection, **kwargs):
        """Can be created with collection and kwargs like a PyMongo GridIn,
        or with a 'delegate' keyword arg, where delegate is a MotorGridIn.
        """
        delegate = kwargs.pop("delegate", None)
        if delegate:
            self.delegate = delegate
        else:
            if not isinstance(collection, Collection):
                raise TypeError("Expected Collection, got %s" % repr(collection))

            self.delegate = motor.MotorGridIn(collection.delegate, **kwargs)

    def __getattr__(self, item):
        return getattr(self.delegate, item)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.synchronize(self.delegate.__aexit__)(exc_type, exc_val, exc_tb)


class SynchroGridOutProperty(object):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, objtype):
        obj.synchronize(obj.delegate.open)()
        return getattr(obj.delegate, self.name)


class GridOut(Synchro):
    __delegate_class__ = motor.MotorGridOut

    _id = SynchroGridOutProperty("_id")
    aliases = SynchroGridOutProperty("aliases")
    chunk_size = SynchroGridOutProperty("chunk_size")
    close = SynchroGridOutProperty("close")
    content_type = SynchroGridOutProperty("content_type")
    filename = SynchroGridOutProperty("filename")
    length = SynchroGridOutProperty("length")
    metadata = SynchroGridOutProperty("metadata")
    name = SynchroGridOutProperty("name")
    upload_date = SynchroGridOutProperty("upload_date")

    def __init__(
        self, root_collection, file_id=None, file_document=None, session=None, delegate=None
    ):
        """Can be created with collection and kwargs like a PyMongo GridOut,
        or with a 'delegate' keyword arg, where delegate is a MotorGridOut.
        """
        if delegate:
            self.delegate = delegate
        else:
            if not isinstance(root_collection, Collection):
                raise TypeError("Expected Collection, got %s" % repr(root_collection))

            self.delegate = motor.MotorGridOut(
                root_collection.delegate, file_id, file_document, session=session
            )

    def __getattr__(self, item):
        self.synchronize(self.delegate.open)()
        return getattr(self.delegate, item)

    def __setattr__(self, key, value):
        # PyMongo's GridOut prohibits setting these values; do the same
        # to make PyMongo's assertRaises tests pass.
        if key in (
            "_id",
            "name",
            "content_type",
            "length",
            "chunk_size",
            "upload_date",
            "aliases",
            "metadata",
            "md5",
        ):
            raise AttributeError()

        super().__setattr__(key, value)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __next__(self):
        try:
            return self.synchronize(self.delegate.__anext__)()
        except StopAsyncIteration:
            raise StopIteration()

    def __iter__(self):
        return self


# Unwrap key_vault_client, pymongo expects it to be a regular MongoClient.
class AutoEncryptionOpts(encryption_options.AutoEncryptionOpts):
    def __init__(self, kms_providers, key_vault_namespace, key_vault_client=None, **kwargs):
        if key_vault_client is not None:
            key_vault_client = key_vault_client.delegate.delegate
        super(AutoEncryptionOpts, self).__init__(
            kms_providers, key_vault_namespace, key_vault_client=key_vault_client, **kwargs
        )


class ClientEncryption(Synchro):
    __delegate_class__ = motor.MotorClientEncryption

    def __init__(
        self,
        kms_providers,
        key_vault_namespace,
        key_vault_client,
        codec_options,
        kms_tls_options=None,
    ):
        self.delegate = motor.MotorClientEncryption(
            kms_providers,
            key_vault_namespace,
            key_vault_client.delegate,
            codec_options,
            kms_tls_options=kms_tls_options,
        )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return self.synchronize(self.delegate.__aexit__)(*args)

    def get_keys(self):
        return Cursor(self.synchronize(self.delegate.get_keys)())
