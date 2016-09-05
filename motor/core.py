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

from __future__ import unicode_literals, absolute_import

"""Framework-agnostic core of Motor, an asynchronous driver for MongoDB."""

import functools
import sys
import textwrap

import pymongo
import pymongo.auth
import pymongo.common
import pymongo.database
import pymongo.errors
import pymongo.mongo_client
import pymongo.mongo_replica_set_client
import pymongo.son_manipulator

from pymongo.bulk import BulkOperationBuilder
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.cursor import Cursor, _QUERY_OPTIONS
from pymongo.command_cursor import CommandCursor

from .metaprogramming import (AsyncCommand,
                              AsyncRead,
                              AsyncWrite,
                              coroutine_annotation,
                              create_class_with_framework,
                              DelegateMethod,
                              motor_coroutine,
                              MotorCursorChainingMethod,
                              ReadOnlyProperty,
                              ReadWriteProperty)
from .motor_common import (callback_type_error,
                           check_deprecated_kwargs,
                           mangle_delegate_name)

HAS_SSL = True
try:
    import ssl
except ImportError:
    ssl = None
    HAS_SSL = False

PY35 = sys.version_info[:2] >= (3, 5)


class AgnosticBase(object):
    def __eq__(self, other):
        # TODO: verify this is well-tested, the isinstance test is tricky.
        if (isinstance(other, self.__class__)
                and hasattr(self, 'delegate')
                and hasattr(other, 'delegate')):
            return self.delegate == other.delegate
        return NotImplemented

    codec_options                   = ReadOnlyProperty()
    name                            = ReadOnlyProperty()
    get_document_class              = DelegateMethod()
    set_document_class              = DelegateMethod()
    document_class                  = ReadWriteProperty()
    read_preference                 = ReadWriteProperty()
    tag_sets                        = ReadWriteProperty()
    secondary_acceptable_latency_ms = ReadWriteProperty()
    write_concern                   = ReadWriteProperty()
    uuid_subtype                    = ReadWriteProperty()

    def __init__(self, delegate):
        self.delegate = delegate

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.delegate)


get_database_doc = """
Get a `MotorDatabase` with the given name and options.

Useful for creating a `MotorDatabase` with different codec options,
read preference, and/or write concern from this `MotorClient`.

  >>> from pymongo import ReadPreference
  >>> client.read_preference == ReadPreference.PRIMARY
  True
  >>> db1 = client.test
  >>> db1.read_preference == ReadPreference.PRIMARY
  True
  >>> db2 = client.get_database(
  ...     'test', read_preference=ReadPreference.SECONDARY)
  >>> db2.read_preference == ReadPreference.SECONDARY
  True

:Parameters:
  - `name`: The name of the database - a string.
  - `codec_options` (optional): An instance of
    :class:`~bson.codec_options.CodecOptions`. If ``None`` (the
    default) the :attr:`codec_options` of this :class:`MongoClient` is
    used.
  - `read_preference` (optional): The read preference to use. If
    ``None`` (the default) the :attr:`read_preference` of this
    :class:`MongoClient` is used. See :mod:`~pymongo.read_preferences`
    for options.
  - `write_concern` (optional): An instance of
    :class:`~pymongo.write_concern.WriteConcern`. If ``None`` (the
    default) the :attr:`write_concern` of this :class:`MongoClient` is
    used.

.. versionadded:: 2.9
"""


class AgnosticClientBase(AgnosticBase):
    """MotorClient and MotorReplicaSetClient common functionality."""
    _ensure_connected  = AsyncRead()
    address            = ReadOnlyProperty()
    alive              = AsyncRead()
    close              = DelegateMethod()
    close_cursor       = AsyncCommand()
    database_names     = AsyncRead()
    disconnect         = DelegateMethod()
    drop_database      = AsyncCommand().unwrap('MotorDatabase')
    get_database       = DelegateMethod(doc=get_database_doc)
    is_mongos          = ReadOnlyProperty()
    is_primary         = ReadOnlyProperty()
    local_threshold_ms = ReadOnlyProperty()
    max_bson_size      = ReadOnlyProperty()
    max_message_size   = ReadOnlyProperty()
    max_pool_size      = ReadOnlyProperty()
    max_wire_version   = ReadOnlyProperty()
    min_wire_version   = ReadOnlyProperty()
    server_info        = AsyncRead()
    tz_aware           = ReadOnlyProperty()

    def __init__(self, io_loop, *args, **kwargs):
        check_deprecated_kwargs(kwargs)
        kwargs['_connect'] = False
        delegate = self.__delegate_class__(*args, **kwargs)
        super(AgnosticClientBase, self).__init__(delegate)
        if io_loop:
            self._framework.check_event_loop(io_loop)
            self.io_loop = io_loop
        else:
            self.io_loop = self._framework.get_event_loop()

    def get_io_loop(self):
        return self.io_loop

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(
                "%s has no attribute %r. To access the %s"
                " database, use client['%s']." % (
                    self.__class__.__name__, name, name, name))

        return self[name]

    def __getitem__(self, name):
        db_class = create_class_with_framework(
            AgnosticDatabase, self._framework, self.__module__)

        return db_class(self, name)

    def get_default_database(self):
        """Get the database named in the MongoDB connection URI.

        .. doctest::

          >>> uri = 'mongodb://localhost/my_database'
          >>> client = MotorClient(uri)
          >>> db = client.get_default_database()
          >>> assert db.name == 'my_database'

        Useful in scripts where you want to choose which database to use
        based only on the URI in a configuration file.
        """
        attr_name = mangle_delegate_name(
            self.__class__,
            '__default_database_name')

        default_db_name = getattr(self.delegate, attr_name)
        if default_db_name is None:
            raise pymongo.errors.ConfigurationError(
                'No default database defined')

        return self[default_db_name]


class AgnosticClient(AgnosticClientBase):
    __motor_class_name__ = 'MotorClient'
    __delegate_class__ = pymongo.mongo_client.MongoClient

    kill_cursors = AsyncCommand()
    fsync        = AsyncCommand()
    unlock       = AsyncCommand()
    nodes        = ReadOnlyProperty()
    host         = ReadOnlyProperty()
    port         = ReadOnlyProperty()

    _simple_command = AsyncRead(attr_name='__simple_command')
    _socket         = AsyncRead(attr_name='__socket')

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
            io_loop = self._framework.get_event_loop()

        # Our class is not actually AgnosticClient here, it's the version of
        # 'MotorClient' that create_class_with_framework created.
        super(self.__class__, self).__init__(io_loop, *args, **kwargs)

    @coroutine_annotation
    def open(self, callback=None):
        """Connect to the server.

        Takes an optional callback, or returns a Future that resolves to
        ``self`` when opened. This is convenient for checking at program
        startup time whether you can connect.

        .. doctest::

          >>> from tornado.ioloop import IOLoop
          >>> from motor.motor_tornado import MotorClient
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
        return self._framework.future_or_callback(self._ensure_connected(True),
                                                  callback,
                                                  self.get_io_loop(),
                                                  self)

    def _get_member(self):
        # TODO: expose the PyMongo Member, or otherwise avoid this.
        return self.delegate._MongoClient__member

    def _get_pools(self):
        member = self._get_member()
        return [member.pool] if member else [None]

    def _get_primary_pool(self):
        return self._get_pools()[0]


class AgnosticReplicaSetClient(AgnosticClientBase):
    __motor_class_name__ = 'MotorReplicaSetClient'
    __delegate_class__ = pymongo.mongo_replica_set_client.MongoReplicaSetClient

    primary     = ReadOnlyProperty()
    secondaries = ReadOnlyProperty()
    arbiters    = ReadOnlyProperty()
    hosts       = ReadOnlyProperty()
    seeds       = DelegateMethod()
    close       = DelegateMethod()

    _simple_command = AsyncRead(attr_name='__simple_command')
    _socket         = AsyncRead(attr_name='__socket')

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
            io_loop = self._framework.get_event_loop()

        # Our class is not actually AgnosticClient here, it's the version of
        # 'MotorClient' that create_class_with_framework created.
        super(self.__class__, self).__init__(io_loop, *args, **kwargs)

    def open(self, callback=None):
        """Connect to the server.

        Takes an optional callback, or returns a Future that resolves to
        ``self`` when opened. This is convenient for checking at program
        startup time whether you can connect.

        .. Not a doctest: don't require a replica set for doctests to pass.

        .. code-block:: python

          >>> from tornado.ioloop import IOLoop
          >>> from motor.motor_tornado import MotorReplicaSetClient
          >>> uri = 'mongodb://localhost:27017/?replicaSet=rs'
          >>> client = MotorReplicaSetClient(uri)
          >>> # run_sync() returns the open client.
          >>> IOLoop.current().run_sync(client.open)
          MotorReplicaSetClient(MongoReplicaSetClient(['localhost:27017', ...]))

        ``open`` raises a :exc:`~pymongo.errors.ConnectionFailure` if it
        cannot connect, but note that auth failures aren't revealed until
        you attempt an operation on the open client.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)

        .. versionchanged:: 0.2
           :class:`MotorReplicaSetClient` now opens itself on demand, calling
           ``open`` explicitly is now optional.
        """
        loop = self.get_io_loop()

        # Once _ensure_connected returns, check if we actually connected, then
        # return "self".
        chained = self._framework.get_future(loop)
        self._framework.add_future(
            loop,
            self._ensure_connected(sync=True),
            self._connected_callback, chained)

        return self._framework.future_or_callback(chained, callback, loop)

    def _connected_callback(self, chained, future):
        try:
            future.result()
        except Exception as error:
            # TODO: exc_info.
            chained.set_exception(error)
        else:
            # Did we actually connect?
            try:
                if self._get_member():
                    chained.set_result(self)
                    return
            except Exception as error:
                # _get_member() can raise ConfigurationError.
                chained.set_exception(error)
                return

            error = pymongo.errors.AutoReconnect('no primary is available')
            chained.set_exception(error)

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


class AgnosticDatabase(AgnosticBase):
    __motor_class_name__ = 'MotorDatabase'
    __delegate_class__ = Database

    add_user            = AsyncCommand()
    authenticate        = AsyncCommand()
    collection_names    = AsyncRead()
    command             = AsyncCommand()
    create_collection   = AsyncCommand().wrap(Collection)
    current_op          = AsyncRead()
    dereference         = AsyncRead()
    drop_collection     = AsyncCommand().unwrap('MotorCollection')
    error               = AsyncRead(doc="OBSOLETE")
    eval                = AsyncCommand()
    get_collection      = DelegateMethod()
    last_status         = AsyncRead(doc="OBSOLETE")
    logout              = AsyncCommand()
    previous_error      = AsyncRead(doc="OBSOLETE")
    profiling_info      = AsyncRead()
    profiling_level     = AsyncRead()
    remove_user         = AsyncCommand()
    reset_error_history = AsyncCommand(doc="OBSOLETE")
    set_profiling_level = AsyncCommand()
    validate_collection = AsyncRead().unwrap('MotorCollection')

    incoming_manipulators         = ReadOnlyProperty()
    incoming_copying_manipulators = ReadOnlyProperty()
    outgoing_manipulators         = ReadOnlyProperty()
    outgoing_copying_manipulators = ReadOnlyProperty()

    def __init__(self, connection, name):
        if not isinstance(connection, AgnosticClientBase):
            raise TypeError("First argument to MotorDatabase must be "
                            "a Motor client, not %r" % connection)

        # "client" is modern, "connection" is deprecated.
        self.client = self.connection = connection
        delegate = Database(connection.delegate, name)
        super(self.__class__, self).__init__(delegate)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(
                "%s has no attribute %r. To access the %s"
                " collection, use database['%s']." % (
                    self.__class__.__name__, name, name, name))

        return self[name]

    def __getitem__(self, name):
        collection_class = create_class_with_framework(
            AgnosticCollection, self._framework, self.__module__)

        return collection_class(self, name)

    def __call__(self, *args, **kwargs):
        database_name = self.delegate.name
        client_class_name = self.connection.__class__.__name__
        if database_name == 'open_sync':
            raise TypeError(
                "%s.open_sync() is unnecessary Motor 0.2, "
                "see changelog for details." % client_class_name)

        raise TypeError(
            "MotorDatabase object is not callable. If you meant to "
            "call the '%s' method on a %s object it is "
            "failing because no such method exists." % (
            database_name, client_class_name))

    def wrap(self, collection):
        # Replace pymongo.collection.Collection with MotorCollection.
        return self[collection.name]

    def add_son_manipulator(self, manipulator):
        """Add a new son manipulator to this database.

        Newly added manipulators will be applied before existing ones.

        :Parameters:
          - `manipulator`: the manipulator to add
        """
        # We override add_son_manipulator to unwrap the AutoReference's
        # database attribute.
        if isinstance(manipulator, pymongo.son_manipulator.AutoReference):
            db = manipulator.database
            db_class = create_class_with_framework(
                AgnosticDatabase,
                self._framework,
                self.__module__)

            if isinstance(db, db_class):
                # db is a MotorDatabase; get the PyMongo Database instance.
                manipulator.database = db.delegate

        self.delegate.add_son_manipulator(manipulator)

    def get_io_loop(self):
        return self.connection.get_io_loop()

mr_doc = """Perform a map/reduce operation on this collection.

If `full_response` is ``False`` (default) returns a
`MotorCollection` instance containing
the results of the operation. Otherwise, returns the full
response from the server to the `map reduce command`_.

:Parameters:
  - `map`: map function (as a JavaScript string)
  - `reduce`: reduce function (as a JavaScript string)
  - `out`: output collection name or `out object` (dict). See
    the `map reduce command`_ documentation for available options.
    Note: `out` options are order sensitive. :class:`~bson.son.SON`
    can be used to specify multiple options.
    e.g. SON([('replace', <collection name>), ('db', <database name>)])
  - `full_response` (optional): if ``True``, return full response to
    this command - otherwise just return the result collection
  - `callback` (optional): function taking (result, error), executed when
    operation completes.
  - `**kwargs` (optional): additional arguments to the
    `map reduce command`_ may be passed as keyword arguments to this
    helper method, e.g.::

       result = yield db.test.map_reduce(map, reduce, "myresults", limit=2)

If a callback is passed, returns None, else returns a Future.

.. note:: The :meth:`map_reduce` method does **not** obey the
   :attr:`read_preference` of this `MotorCollection`. To run
   mapReduce on a secondary use the `inline_map_reduce` method
   instead.

.. _map reduce command: http://docs.mongodb.org/manual/reference/command/mapReduce/

.. mongodoc:: mapreduce
"""


# PyMongo's Collection.update shows examples that don't apply to Motor.
update_doc = """Update a document(s) in this collection.

Raises :class:`TypeError` if either `spec` or `document` is
not an instance of ``dict`` or `upsert` is not an instance of
``bool``.

Write concern options can be passed as keyword arguments, overriding
any global defaults. Valid options include w=<int/string>,
wtimeout=<int>, j=<bool>, or fsync=<bool>. See the parameter list below
for a detailed explanation of these options.

There are many useful `update modifiers`_ which can be used
when performing updates. For example, here we use the
``"$set"`` modifier to modify a field in a matching document:

  >>> @gen.coroutine
  ... def do_update():
  ...     result = yield collection.update({'_id': 10},
  ...                                      {'$set': {'x': 1}})

:Parameters:
  - `spec`: a ``dict`` or :class:`~bson.son.SON` instance
    specifying elements which must be present for a document
    to be updated
  - `document`: a ``dict`` or :class:`~bson.son.SON`
    instance specifying the document to be used for the update
    or (in the case of an upsert) insert - see docs on MongoDB
    `update modifiers`_
  - `upsert` (optional): perform an upsert if ``True``
  - `manipulate` (optional): manipulate the document before
    updating? If ``True`` all instances of
    :mod:`~pymongo.son_manipulator.SONManipulator` added to
    this :class:`~pymongo.database.Database` will be applied
    to the document before performing the update.
  - `check_keys` (optional): check if keys in `document` start
    with '$' or contain '.', raising
    :class:`~pymongo.errors.InvalidName`. Only applies to
    document replacement, not modification through $
    operators.
  - `safe` (optional): **DEPRECATED** - Use `w` instead.
  - `multi` (optional): update all documents that match
    `spec`, rather than just the first matching document. The
    default value for `multi` is currently ``False``, but this
    might eventually change to ``True``. It is recommended
    that you specify this argument explicitly for all update
    operations in order to prepare your code for that change.
  - `w` (optional): (integer or string) If this is a replica set, write
    operations will block until they have been replicated to the
    specified number or tagged set of servers. `w=<int>` always includes
    the replica set primary (e.g. w=3 means write to the primary and wait
    until replicated to **two** secondaries). **Passing w=0 disables
    write acknowledgement and all other write concern options.**
  - `wtimeout` (optional): (integer) Used in conjunction with `w`.
    Specify a value in milliseconds to control how long to wait for
    write propagation to complete. If replication does not complete in
    the given timeframe, a timeout exception is raised.
  - `j` (optional): If ``True`` block until write operations have been
    committed to the journal. Ignored if the server is running without
    journaling.
  - `fsync` (optional): If ``True`` force the database to fsync all
    files before returning. When used with `j` the server awaits the
    next group commit before returning.

:Returns:
  - A document (dict) describing the effect of the update.

.. _update modifiers: http://www.mongodb.org/display/DOCS/Updating

.. mongodoc:: update"""


class AgnosticCollection(AgnosticBase):
    __motor_class_name__ = 'MotorCollection'
    __delegate_class__ = Collection

    bulk_write           = AsyncCommand()
    count                = AsyncRead()
    create_index         = AsyncCommand()
    delete_many          = AsyncCommand()
    delete_one           = AsyncCommand()
    distinct             = AsyncRead()
    drop                 = AsyncCommand()
    drop_index           = AsyncCommand()
    drop_indexes         = AsyncCommand()
    ensure_index         = AsyncCommand()
    find_and_modify      = AsyncCommand()
    find_one             = AsyncRead()
    find_one_and_delete  = AsyncCommand()
    find_one_and_replace = AsyncCommand()
    find_one_and_update  = AsyncCommand()
    full_name            = ReadOnlyProperty()
    group                = AsyncRead()
    index_information    = AsyncRead()
    inline_map_reduce    = AsyncRead()
    insert               = AsyncWrite()
    insert_many          = AsyncWrite()
    insert_one           = AsyncCommand()
    map_reduce           = AsyncCommand(doc=mr_doc).wrap(Collection)
    options              = AsyncRead()
    reindex              = AsyncCommand()
    remove               = AsyncWrite()
    rename               = AsyncCommand()
    replace_one          = AsyncCommand()
    save                 = AsyncWrite()
    update               = AsyncWrite(doc=update_doc)
    update_many          = AsyncCommand()
    update_one           = AsyncCommand()
    with_options         = DelegateMethod()

    _async_aggregate  = AsyncRead(attr_name='aggregate')
    __parallel_scan   = AsyncRead(attr_name='parallel_scan')

    def __init__(self, database, name):
        db_class = create_class_with_framework(
            AgnosticDatabase, self._framework, self.__module__)

        if not isinstance(database, db_class):
            raise TypeError("First argument to MotorCollection must be "
                            "MotorDatabase, not %r" % database)

        delegate = Collection(database.delegate, name)
        super(self.__class__, self).__init__(delegate)
        self.database = database

    def __getattr__(self, name):
        # Dotted collection name, like "foo.bar".
        if name.startswith('_'):
            full_name = "%s.%s" % (self.name, name)
            raise AttributeError(
                "%s has no attribute %r. To access the %s"
                " collection, use database['%s']." % (
                    self.__class__.__name__, name, full_name, full_name))

        return self[name]

    def __getitem__(self, name):
        collection_class = create_class_with_framework(
            AgnosticCollection, self._framework, self.__module__)

        return collection_class(self.database, self.name + '.' + name)

    def __call__(self, *args, **kwargs):
        raise TypeError(
            "MotorCollection object is not callable. If you meant to "
            "call the '%s' method on a MotorCollection object it is "
            "failing because no such method exists." %
            self.delegate.name)

    def find(self, *args, **kwargs):
        """Create a :class:`MotorCursor`. Same parameters as for
        PyMongo's :meth:`~pymongo.collection.Collection.find`.

        Note that ``find`` does not take a `callback` parameter, nor does
        it return a Future, because ``find`` merely creates a
        :class:`MotorCursor` without performing any operations on the server.
        ``MotorCursor`` methods such as :meth:`~MotorCursor.to_list` or
        :meth:`~MotorCursor.count` perform actual operations.
        """
        if 'callback' in kwargs:
            raise pymongo.errors.InvalidOperation(
                "Pass a callback to each, to_list, or count, not to find.")

        cursor = self.delegate.find(*args, **kwargs)
        cursor_class = create_class_with_framework(
            AgnosticCursor, self._framework, self.__module__)

        return cursor_class(cursor, self)

    def aggregate(self, pipeline, **kwargs):
        """Execute an aggregation pipeline on this collection.

        The aggregation can be run on a secondary if the client is a
        :class:`~motor.MotorReplicaSetClient` and its ``read_preference`` is not
        :attr:`PRIMARY`.

        :Parameters:
          - `pipeline`: a single command or list of aggregation commands
          - `**kwargs`: send arbitrary parameters to the aggregate command

        Returns a `MotorCommandCursor` that can be iterated like a cursor from
        `find`::

          pipeline = [{'$project': {'name': {'$toUpper': '$name'}}}]
          cursor = collection.aggregate(pipeline)
          while (yield cursor.fetch_next):
              doc = cursor.next_object()
              print(doc)

        In Python 3.5 and newer, aggregation cursors can be iterated elegantly
        in native coroutines with `async for`::

          async def f():
              async for doc in collection.aggregate(pipeline):
                  doc = cursor.next_object()
                  print(doc)

        MongoDB versions 2.4 and older do not support aggregation cursors; use
        ``yield`` and pass ``cursor=False`` for compatibility with older
        MongoDBs::

          reply = yield collection.aggregate(cursor=False)
          for doc in reply['results']:
              print(doc)

        .. versionchanged:: 0.5
           `aggregate` now returns a cursor by default, and the cursor is
           returned immediately without a ``yield``.
           See :ref:`aggregation changes in Motor 0.5 <aggregate_changes_0_5>`.

        .. versionchanged:: 0.2
           Added cursor support.

        .. _aggregate command:
            http://docs.mongodb.org/manual/applications/aggregation

        """
        if kwargs.get('cursor') is False:
            kwargs.pop('cursor')
            # One-shot aggregation, no cursor. Send command now, return Future.
            return self._async_aggregate(pipeline, **kwargs)
        else:
            if 'callback' in kwargs:
                raise pymongo.errors.InvalidOperation(
                    "Pass a callback to to_list or each, not to aggregate.")

            kwargs.setdefault('cursor', {})
            cursor_class = create_class_with_framework(
                AgnosticAggregationCursor, self._framework, self.__module__)

            # Latent cursor that will send initial command on first "async for".
            return cursor_class(self, pipeline, **kwargs)

    def parallel_scan(self, num_cursors, **kwargs):
        """Scan this entire collection in parallel.

        Returns a list of up to ``num_cursors`` cursors that can be iterated
        concurrently. As long as the collection is not modified during
        scanning, each document appears once in one of the cursors' result
        sets.

        For example, to process each document in a collection using some
        function ``process_document()``::

            @gen.coroutine
            def process_cursor(cursor):
                while (yield cursor.fetch_next):
                    process_document(cursor.next_object())

            # Get up to 4 cursors.
            cursors = yield collection.parallel_scan(4)
            yield [process_cursor(cursor) for cursor in cursors]

            # All documents have now been processed.

        If ``process_document()`` is a coroutine, do
        ``yield process_document(document)``.

        With :class:`MotorReplicaSetClient`, pass `read_preference` of
        :attr:`~pymongo.read_preference.ReadPreference.SECONDARY_PREFERRED`
        to scan a secondary.

        :Parameters:
          - `num_cursors`: the number of cursors to return

        .. note:: Requires server version **>= 2.5.5**.
        """
        io_loop = self.get_io_loop()
        original_future = self._framework.get_future(io_loop)

        # Return a future, or if user passed a callback chain it to the future.
        callback = kwargs.pop('callback', None)
        retval = self._framework.future_or_callback(original_future,
                                                    callback,
                                                    io_loop)

        # Once we have PyMongo Cursors, wrap in MotorCursors and resolve the
        # future with them, or pass them to the callback.
        self._framework.add_future(
            io_loop,
            self.__parallel_scan(num_cursors, **kwargs),
            self._scan_callback, original_future)

        return retval

    def _scan_callback(self, original_future, future):
        try:
            command_cursors = future.result()
        except Exception as exc:
            original_future.set_exception(exc)
        else:
            command_cursor_class = create_class_with_framework(
                AgnosticCommandCursor, self._framework, self.__module__)

            motor_command_cursors = [
                command_cursor_class(cursor, self)
                for cursor in command_cursors]

            original_future.set_result(motor_command_cursors)

    def initialize_unordered_bulk_op(self):
        """Initialize an unordered batch of write operations.

        Operations will be performed on the server in arbitrary order,
        possibly in parallel. All operations will be attempted.

        Returns a :class:`~motor.MotorBulkOperationBuilder` instance.

        See :ref:`unordered_bulk` for examples.

        .. versionadded:: 0.2
        """
        bob_class = create_class_with_framework(
            AgnosticBulkOperationBuilder, self._framework, self.__module__)

        return bob_class(self, ordered=False)

    def initialize_ordered_bulk_op(self):
        """Initialize an ordered batch of write operations.

        Operations will be performed on the server serially, in the
        order provided. If an error occurs all remaining operations
        are aborted.

        Returns a :class:`~motor.MotorBulkOperationBuilder` instance.

        See :ref:`ordered_bulk` for examples.

        .. versionadded:: 0.2
        """
        bob_class = create_class_with_framework(
            AgnosticBulkOperationBuilder,
            self._framework,
            self.__module__)

        return bob_class(self, ordered=True)

    def wrap(self, obj):
        if obj.__class__ is Collection:
            # Replace pymongo.collection.Collection with MotorCollection.
            return self.database[obj.name]
        elif obj.__class__ is Cursor:
            return AgnosticCursor(obj, self)
        elif obj.__class__ is CommandCursor:
            command_cursor_class = create_class_with_framework(
                AgnosticCommandCursor,
                self._framework,
                self.__module__)

            return command_cursor_class(obj, self)
        else:
            return obj

    def get_io_loop(self):
        return self.database.get_io_loop()


class AgnosticBaseCursor(AgnosticBase):
    """Base class for AgnosticCursor and AgnosticCommandCursor"""
    _refresh      = AsyncRead()
    cursor_id     = ReadOnlyProperty()
    alive         = ReadOnlyProperty()
    batch_size    = MotorCursorChainingMethod()

    def __init__(self, cursor, collection):
        """Don't construct a cursor yourself, but acquire one from methods like
        :meth:`MotorCollection.find` or :meth:`MotorCollection.aggregate`.

        .. note::
          There is no need to manually close cursors; they are closed
          by the server after being fully iterated
          with :meth:`to_list`, :meth:`each`, or :attr:`fetch_next`, or
          automatically closed by the client when the :class:`MotorCursor` is
          cleaned up by the garbage collector.
        """
        # 'cursor' is a PyMongo Cursor, CommandCursor, or a _LatentCursor.
        super(AgnosticBaseCursor, self).__init__(delegate=cursor)
        self.collection = collection
        self.started = False
        self.closed = False

    if PY35:
        exec(textwrap.dedent("""
        async def __aiter__(self):
            return self

        async def __anext__(self):
            # An optimization: skip the "await" if possible.
            if self._buffer_size() or await self.fetch_next:
                return self.next_object()
            raise StopAsyncIteration()
        """), globals(), locals())

    def _get_more(self):
        """Initial query or getMore. Returns a Future."""
        if not self.alive:
            raise pymongo.errors.InvalidOperation(
                "Can't call get_more() on a MotorCursor that has been"
                " exhausted or killed.")

        self.started = True
        return self._refresh()

    @property
    @coroutine_annotation
    def fetch_next(self):
        """A Future used with `gen.coroutine`_ to asynchronously retrieve the
        next document in the result set, fetching a batch of documents from the
        server if necessary. Resolves to ``False`` if there are no more
        documents, otherwise :meth:`next_object` is guaranteed to return a
        document.

        .. _`gen.coroutine`: http://tornadoweb.org/en/stable/gen.html

        .. testsetup:: fetch_next

          MongoClient().test.test_collection.remove()
          collection = MotorClient().test.test_collection

        .. doctest:: fetch_next

          >>> @gen.coroutine
          ... def f():
          ...     yield collection.insert([{'_id': i} for i in range(5)])
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     while (yield cursor.fetch_next):
          ...         doc = cursor.next_object()
          ...         sys.stdout.write(str(doc['_id']) + ', ')
          ...     print('done')
          ...
          >>> IOLoop.current().run_sync(f)
          0, 1, 2, 3, 4, done

        While it appears that fetch_next retrieves each document from
        the server individually, the cursor actually fetches documents
        efficiently in `large batches`_.

        In Python 3.5 and newer, cursors can be iterated elegantly and very
        efficiently in native coroutines with `async for`:

        .. doctest:: fetch_next

          >>> async def f():
          ...     async for doc in collection.find():
          ...         sys.stdout.write(str(doc['_id']) + ', ')
          ...     print('done')
          ...
          >>> IOLoop.current().run_sync(f)
          0, 1, 2, 3, 4, done

        .. _`large batches`: http://docs.mongodb.org/manual/core/read-operations/#cursor-behaviors
        """
        if not self._buffer_size() and self.alive:
            # Return the Future, which resolves to number of docs fetched or 0.
            return self._get_more()
        elif self._buffer_size():
            future = self._framework.get_future(self.get_io_loop())
            future.set_result(True)
            return future
        else:
            # Dead
            future = self._framework.get_future(self.get_io_loop())
            future.set_result(False)
            return future

    def next_object(self):
        """Get a document from the most recently fetched batch, or ``None``.
        See :attr:`fetch_next`.
        """
        if not self._buffer_size():
            return None
        return next(self.delegate)

    def each(self, callback):
        """Iterates over all the documents for this cursor.

        `each` returns immediately, and `callback` is executed asynchronously
        for each document. `callback` is passed ``(None, None)`` when iteration
        is complete.

        Cancel iteration early by returning ``False`` from the callback. (Only
        ``False`` cancels iteration: returning ``None`` or 0 does not.)

        .. testsetup:: each

          from tornado.ioloop import IOLoop
          MongoClient().test.test_collection.remove()
          collection = MotorClient().test.test_collection

        .. doctest:: each

          >>> def inserted(result, error):
          ...     if error:
          ...         raise error
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     cursor.each(callback=each)
          ...
          >>> def each(result, error):
          ...     if error:
          ...         raise error
          ...     elif result:
          ...         sys.stdout.write(str(result['_id']) + ', ')
          ...     else:
          ...         # Iteration complete
          ...         IOLoop.current().stop()
          ...         print('done')
          ...
          >>> collection.insert(
          ...     [{'_id': i} for i in range(5)], callback=inserted)
          >>> IOLoop.current().start()
          0, 1, 2, 3, 4, done

        .. note:: Unlike other Motor methods, ``each`` requires a callback and
           does not return a Future, so it cannot be used with
           ``gen.coroutine.`` :meth:`to_list` or :attr:`fetch_next` are much
           easier to use.

        :Parameters:
         - `callback`: function taking (document, error)
        """
        if not callable(callback):
            raise callback_type_error

        self._each_got_more(callback, None)

    def _each_got_more(self, callback, future):
        if future:
            try:
                future.result()
            except Exception as error:
                callback(None, error)
                return

        while self._buffer_size() > 0:
            doc = next(self.delegate)  # decrements self.buffer_size

            # Quit if callback returns exactly False (not None). Note we
            # don't close the cursor: user may want to resume iteration.
            if callback(doc, None) is False:
                return

            # The callback closed this cursor?
            if self.closed:
                return

        if self.alive and (self.cursor_id or not self.started):
            self._framework.add_future(
                self.get_io_loop(),
                self._get_more(),
                self._each_got_more, callback)
        else:
            # Complete
            self._framework.call_soon(
                self.get_io_loop(),
                functools.partial(callback, None, None))

    @coroutine_annotation
    def to_list(self, length, callback=None):
        """Get a list of documents.

        .. testsetup:: to_list

          MongoClient().test.test_collection.remove()
          from tornado import ioloop

        .. doctest:: to_list

          >>> from motor.motor_tornado import MotorClient
          >>> collection = MotorClient().test.test_collection
          >>>
          >>> @gen.coroutine
          ... def f():
          ...     yield collection.insert([{'_id': i} for i in range(4)])
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     docs = yield cursor.to_list(length=2)
          ...     while docs:
          ...         print(docs)
          ...         docs = yield cursor.to_list(length=2)
          ...
          ...     print('done')
          ...
          >>> ioloop.IOLoop.current().run_sync(f)
          [{'_id': 0}, {'_id': 1}]
          [{'_id': 2}, {'_id': 3}]
          done

        :Parameters:
         - `length`: maximum number of documents to return for this call, or
           None
         - `callback` (optional): function taking (documents, error)

        If a callback is passed, returns None, else returns a Future.

        .. versionchanged:: 0.2
           `callback` must be passed as a keyword argument, like
           ``to_list(10, callback=callback)``, and the
           `length` parameter is no longer optional.
        """
        if length is not None:
            if not isinstance(length, int):
                raise TypeError('length must be an int, not %r' % length)
            elif length < 0:
                raise ValueError('length must be non-negative')

        if self._query_flags() & _QUERY_OPTIONS['tailable_cursor']:
            raise pymongo.errors.InvalidOperation(
                "Can't call to_list on tailable cursor")

        to_list_future = self._framework.get_future(self.get_io_loop())

        # Run future_or_callback's type checking before we change anything.
        retval = self._framework.future_or_callback(to_list_future,
                                                    callback,
                                                    self.get_io_loop())

        if not self.alive:
            to_list_future.set_result([])
        else:
            the_list = []
            self._framework.add_future(
                self.get_io_loop(),
                self._get_more(),
                self._to_list, length, the_list, to_list_future)

        return retval

    def _to_list(self, length, the_list, to_list_future, get_more_result):
        # get_more_result is the result of self._get_more().
        # to_list_future will be the result of the user's to_list() call.
        try:
            result = get_more_result.result()
            collection = self.collection
            fix_outgoing = collection.database.delegate._fix_outgoing

            if length is None:
                n = result
            else:
                n = min(length, result)

            for _ in range(n):
                the_list.append(fix_outgoing(self._data().popleft(),
                                             collection))

            reached_length = (length is not None and len(the_list) >= length)
            if reached_length or not self.alive:
                to_list_future.set_result(the_list)
            else:
                self._framework.add_future(
                    self.get_io_loop(),
                    self._get_more(),
                    self._to_list, length, the_list, to_list_future)
        except Exception as exc:
            # TODO: lost exc_info
            to_list_future.set_exception(exc)

    def get_io_loop(self):
        return self.collection.get_io_loop()

    @motor_coroutine
    def close(self):
        """Explicitly kill this cursor on the server. Call like (in Tornado)::

           yield cursor.close()

        :Parameters:
         - `callback` (optional): function taking (result, error).

        If a callback is passed, returns None, else returns a Future.
        """
        if not self.closed:
            self.closed = True
            yield self._framework.yieldable(self._close())

    def _buffer_size(self):
        return len(self._data())

    # Paper over some differences between PyMongo Cursor and CommandCursor.
    def _query_flags(self):
        raise NotImplementedError

    def _data(self):
        raise NotImplementedError

    def _clear_cursor_id(self):
        raise NotImplementedError

    def _close_exhaust_cursor(self):
        raise NotImplementedError

    def _killed(self):
        raise NotImplementedError

    @motor_coroutine
    def _close(self):
        raise NotImplementedError()


class AgnosticCursor(AgnosticBaseCursor):
    __motor_class_name__ = 'MotorCursor'
    __delegate_class__ = Cursor
    address       = ReadOnlyProperty()
    count         = AsyncRead()
    distinct      = AsyncRead()
    explain       = AsyncRead()
    add_option    = MotorCursorChainingMethod()
    remove_option = MotorCursorChainingMethod()
    limit         = MotorCursorChainingMethod()
    skip          = MotorCursorChainingMethod()
    max_scan      = MotorCursorChainingMethod()
    sort          = MotorCursorChainingMethod(doc="""
Sorts this cursor's results.

Pass a field name and a direction, either
:data:`~pymongo.ASCENDING` or :data:`~pymongo.DESCENDING`:

.. testsetup:: sort

  MongoClient().test.test_collection.drop()
  MongoClient().test.test_collection.insert([
      {'_id': i, 'field1': i % 2, 'field2': i}
      for i in range(5)])
  collection = MotorClient().test.test_collection

.. doctest:: sort

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find().sort('_id', pymongo.DESCENDING)
  ...     docs = yield cursor.to_list(None)
  ...     print([d['_id'] for d in docs])
  ...
  >>> IOLoop.current().run_sync(f)
  [4, 3, 2, 1, 0]

To sort by multiple fields, pass a list of (key, direction) pairs:

.. doctest:: sort

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find().sort([
  ...         ('field1', pymongo.ASCENDING),
  ...         ('field2', pymongo.DESCENDING)])
  ...
  ...     docs = yield cursor.to_list(None)
  ...     print([(d['field1'], d['field2']) for d in docs])
  ...
  >>> IOLoop.current().run_sync(f)
  [(0, 4), (0, 2), (0, 0), (1, 3), (1, 1)]

Beginning with MongoDB version 2.6, text search results can be
sorted by relevance:

.. testsetup:: sort_text

  MongoClient().test.test_collection.drop()
  MongoClient().test.test_collection.insert([
      {'field': 'words'},
      {'field': 'words about some words'}])

  MongoClient().test.test_collection.create_index([('field', 'text')])
  collection = MotorClient().test.test_collection

.. doctest:: sort_text

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find({
  ...         '$text': {'$search': 'some words'}},
  ...         {'score': {'$meta': 'textScore'}})
  ...
  ...     # Sort by 'score' field.
  ...     cursor.sort([('score', {'$meta': 'textScore'})])
  ...     docs = yield cursor.to_list(None)
  ...     for doc in docs:
  ...         print('%.1f %s' % (doc['score'], doc['field']))
  ...
  >>> IOLoop.current().run_sync(f)
  1.5 words about some words
  1.0 words

Raises :class:`~pymongo.errors.InvalidOperation` if this cursor has
already been used. Only the last :meth:`sort` applied to this
cursor has any effect.

:Parameters:
  - `key_or_list`: a single key or a list of (key, direction)
    pairs specifying the keys to sort on
  - `direction` (optional): only used if `key_or_list` is a single
    key, if not given :data:`~pymongo.ASCENDING` is assumed
""")
    hint          = MotorCursorChainingMethod()
    where         = MotorCursorChainingMethod()
    max_time_ms   = MotorCursorChainingMethod()
    min           = MotorCursorChainingMethod()
    max           = MotorCursorChainingMethod()
    comment       = MotorCursorChainingMethod()

    _Cursor__die  = AsyncRead()

    def rewind(self):
        """Rewind this cursor to its unevaluated state."""
        self.delegate.rewind()
        self.started = False
        return self

    def clone(self):
        """Get a clone of this cursor."""
        return self.__class__(self.delegate.clone(), self.collection)

    def __copy__(self):
        return self.__class__(self.delegate.__copy__(), self.collection)

    def __deepcopy__(self, memo):
        return self.__class__(self.delegate.__deepcopy__(memo), self.collection)

    def _query_flags(self):
        return self.delegate._Cursor__query_flags

    def _data(self):
        return self.delegate._Cursor__data

    def _clear_cursor_id(self):
        self.delegate._Cursor__id = 0

    def _close_exhaust_cursor(self):
        # If an exhaust cursor is dying without fully iterating its results,
        # it must close the socket. PyMongo's Cursor does this, but we've
        # disabled its cleanup so we must do it ourselves.
        if self.delegate._Cursor__exhaust:
            manager = self.delegate._Cursor__exhaust_mgr
            if manager.sock:
                manager.sock.close()

            manager.close()

    def _killed(self):
        return self.delegate._Cursor__killed

    @motor_coroutine
    def _close(self):
        yield self._framework.yieldable(self._Cursor__die())


class AgnosticCommandCursor(AgnosticBaseCursor):
    __motor_class_name__ = 'MotorCommandCursor'
    __delegate_class__ = CommandCursor

    _CommandCursor__die = AsyncRead()

    def _query_flags(self):
        return 0

    def _data(self):
        return self.delegate._CommandCursor__data

    def _clear_cursor_id(self):
        self.delegate._CommandCursor__id = 0

    def _close_exhaust_cursor(self):
        # MongoDB doesn't have exhaust command cursors yet.
        pass

    def _killed(self):
        return self.delegate._CommandCursor__killed

    @motor_coroutine
    def _close(self):
        yield self._framework.yieldable(self._CommandCursor__die())


class _LatentCursor(object):
    """Take the place of a PyMongo CommandCursor until aggregate() begins."""
    alive = True
    _CommandCursor__data = []
    _CommandCursor__id = None
    _CommandCursor__killed = False
    cursor_id = None

    def clone(self):
        return _LatentCursor()

    def rewind(self):
        pass


class AgnosticAggregationCursor(AgnosticCommandCursor):
    __motor_class_name__ = 'MotorAggregationCursor'

    def __init__(self, collection, pipeline, **kwargs):
        # We're being constructed without yield or await, like:
        #
        #     cursor = collection.aggregate(pipeline)
        #
        # ... so we can't send the "aggregate" command to the server and get
        # a PyMongo CommandCursor back yet. Set self.delegate to a latent
        # cursor until the first yield or await triggers _get_more().
        super(self.__class__, self).__init__(_LatentCursor(), collection)
        self.pipeline = pipeline
        self.kwargs = kwargs

    def _get_more(self):
        if not self.started:
            self.started = True
            original_future = self._framework.get_future(self.get_io_loop())
            future = self.collection._async_aggregate(
                self.pipeline,
                **self.kwargs)

            self._framework.add_future(
                self.get_io_loop(),
                future,
                self._on_get_more, original_future)

            return original_future

        return super(self.__class__, self)._get_more()

    def _on_get_more(self, original_future, future):
        try:
            # "result" is a CommandCursor from PyMongo's aggregate().
            self.delegate = future.result()
        except Exception as exc:
            # TODO: exc_info.
            original_future.set_exception(exc)
        else:
            # _get_more is complete.
            original_future.set_result(len(self.delegate._CommandCursor__data))


class AgnosticBulkOperationBuilder(AgnosticBase):
    __motor_class_name__ = 'MotorBulkOperationBuilder'
    __delegate_class__ = BulkOperationBuilder

    find        = DelegateMethod()
    insert      = DelegateMethod()
    execute     = AsyncCommand()

    def __init__(self, collection, ordered):
        self.io_loop = collection.get_io_loop()
        delegate = BulkOperationBuilder(collection.delegate, ordered)
        super(self.__class__, self).__init__(delegate)

    def get_io_loop(self):
        return self.io_loop
