# Copyright 2011-present MongoDB, Inc.
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

from pymongo.change_stream import ChangeStream
from pymongo.client_session import ClientSession
from pymongo.collection import Collection
from pymongo.command_cursor import CommandCursor, RawBatchCommandCursor
from pymongo.cursor import Cursor, RawBatchCursor, _QUERY_OPTIONS
from pymongo.database import Database
from pymongo.driver_info import DriverInfo

from . import version as motor_version
from .metaprogramming import (AsyncCommand,
                              AsyncRead,
                              AsyncWrite,
                              coroutine_annotation,
                              create_class_with_framework,
                              DelegateMethod,
                              motor_coroutine,
                              MotorCursorChainingMethod,
                              ReadOnlyProperty,
                              unwrap_args_session,
                              unwrap_kwargs_session)
from .motor_common import callback_type_error
from motor.docstrings import *

HAS_SSL = True
try:
    import ssl
except ImportError:
    ssl = None
    HAS_SSL = False

PY35 = sys.version_info >= (3, 5)


class AgnosticBase(object):
    def __eq__(self, other):
        if (isinstance(other, self.__class__)
                and hasattr(self, 'delegate')
                and hasattr(other, 'delegate')):
            return self.delegate == other.delegate
        return NotImplemented

    def __init__(self, delegate):
        self.delegate = delegate

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.delegate)


class AgnosticBaseProperties(AgnosticBase):
    codec_options   = ReadOnlyProperty()
    read_preference = ReadOnlyProperty()
    read_concern    = ReadOnlyProperty()
    write_concern   = ReadOnlyProperty()


class AgnosticClient(AgnosticBaseProperties):
    __motor_class_name__ = 'MotorClient'
    __delegate_class__ = pymongo.mongo_client.MongoClient

    address                  = ReadOnlyProperty()
    arbiters                 = ReadOnlyProperty()
    close                    = DelegateMethod()
    drop_database            = AsyncCommand().unwrap('MotorDatabase')
    event_listeners          = ReadOnlyProperty()
    fsync                    = AsyncCommand()
    get_database             = DelegateMethod(doc=get_database_doc).wrap(Database)
    HOST                     = ReadOnlyProperty()
    is_mongos                = ReadOnlyProperty()
    is_primary               = ReadOnlyProperty()
    list_databases           = AsyncRead().wrap(CommandCursor)
    list_database_names      = AsyncRead()
    local_threshold_ms       = ReadOnlyProperty()
    max_bson_size            = ReadOnlyProperty()
    max_idle_time_ms         = ReadOnlyProperty()
    max_message_size         = ReadOnlyProperty()
    max_pool_size            = ReadOnlyProperty()
    max_write_batch_size     = ReadOnlyProperty()
    min_pool_size            = ReadOnlyProperty()
    nodes                    = ReadOnlyProperty()
    PORT                     = ReadOnlyProperty()
    primary                  = ReadOnlyProperty()
    read_concern             = ReadOnlyProperty()
    retry_writes             = ReadOnlyProperty()
    secondaries              = ReadOnlyProperty()
    server_info              = AsyncRead()
    server_selection_timeout = ReadOnlyProperty()
    start_session            = AsyncCommand(doc=start_session_doc).wrap(ClientSession)
    unlock                   = AsyncCommand()

    def __init__(self, *args, **kwargs):
        """Create a new connection to a single MongoDB instance at *host:port*.

        Takes the same constructor arguments as
        :class:`~pymongo.mongo_client.MongoClient`, as well as:

        :Parameters:
          - `io_loop` (optional): Special event loop
            instance to use instead of default
        """
        if 'io_loop' in kwargs:
            io_loop = kwargs.pop('io_loop')
            self._framework.check_event_loop(io_loop)
        else:
            io_loop = self._framework.get_event_loop()

        kwargs.setdefault('connect', False)
        kwargs.setdefault(
            'driver',
            DriverInfo('Motor', motor_version, self._framework.platform_info()))

        delegate = self.__delegate_class__(*args, **kwargs)
        super(AgnosticBaseProperties, self).__init__(delegate)
        self.io_loop = io_loop

    def get_io_loop(self):
        return self.io_loop

    def watch(self, pipeline=None, full_document='default', resume_after=None,
              max_await_time_ms=None, batch_size=None, collation=None,
              start_at_operation_time=None, session=None):
        """Watch changes on this cluster.

        Returns a :class:`~MotorChangeStream` cursor which iterates over changes
        on all databases in this cluster. Introduced in MongoDB 4.0.

        See the documentation for :meth:`MotorCollection.watch` for more
        details and examples.

        :Parameters:
          - `pipeline` (optional): A list of aggregation pipeline stages to
            append to an initial ``$changeStream`` stage. Not all
            pipeline stages are valid after a ``$changeStream`` stage, see the
            MongoDB documentation on change streams for the supported stages.
          - `full_document` (optional): The fullDocument option to pass
            to the ``$changeStream`` stage. Allowed values: 'default',
            'updateLookup'.  Defaults to 'default'.
            When set to 'updateLookup', the change notification for partial
            updates will include both a delta describing the changes to the
            document, as well as a copy of the entire document that was
            changed from some time after the change occurred.
          - `resume_after` (optional): The logical starting point for this
            change stream.
          - `max_await_time_ms` (optional): The maximum time in milliseconds
            for the server to wait for changes before responding to a getMore
            operation.
          - `batch_size` (optional): The maximum number of documents to return
            per batch.
          - `collation` (optional): The :class:`~pymongo.collation.Collation`
            to use for the aggregation.
          - `start_at_operation_time` (optional): If provided, the resulting
            change stream will only return changes that occurred at or after
            the specified :class:`~bson.timestamp.Timestamp`. Requires
            MongoDB >= 4.0.
          - `session` (optional): a
            :class:`~pymongo.client_session.ClientSession`.

        :Returns:
          A :class:`~MotorChangeStream`.

        .. versionadded:: 2.0

        .. mongodoc:: changeStreams
        """
        cursor_class = create_class_with_framework(
            AgnosticChangeStream, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, pipeline, full_document, resume_after,
                            max_await_time_ms, batch_size, collation,
                            start_at_operation_time, session)

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

    def wrap(self, obj):
        if obj.__class__ == Database:
            db_class = create_class_with_framework(
                AgnosticDatabase,
                self._framework,
                self.__module__)

            return db_class(self, obj.name, _delegate=obj)
        elif obj.__class__ == CommandCursor:
            command_cursor_class = create_class_with_framework(
                AgnosticCommandCursor,
                self._framework,
                self.__module__)

            return command_cursor_class(obj, self)
        elif obj.__class__ == ClientSession:
            session_class = create_class_with_framework(
                AgnosticClientSession,
                self._framework,
                self.__module__)

            return session_class(obj, self)


class _MotorTransactionContext(object):
    """Internal transaction context manager for start_transaction."""
    def __init__(self, session):
        self._session = session

    if PY35:
        exec(textwrap.dedent("""
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._session.delegate._in_transaction:
                if exc_val is None:
                    await self._session.commit_transaction()
                else:
                    await self._session.abort_transaction()
        """), globals(), locals())


class AgnosticClientSession(AgnosticBase):
    """A session for ordering sequential operations.

    Do not create an instance of :class:`MotorClientSession` directly; use
    :meth:`MotorClient.start_session`:

    .. code-block:: python3

      collection = client.db.collection

      async with await client.start_session() as s:
          async with s.start_transaction():
              await collection.delete_one({'x': 1}, session=s)
              await collection.insert_one({'x': 2}, session=s)

    .. versionadded:: 2.0
    """

    __motor_class_name__ = 'MotorClientSession'
    __delegate_class__ = ClientSession

    commit_transaction     = AsyncCommand()
    abort_transaction      = AsyncCommand()
    end_session            = AsyncCommand()
    cluster_time           = ReadOnlyProperty()
    has_ended              = ReadOnlyProperty()
    options                = ReadOnlyProperty()
    operation_time         = ReadOnlyProperty()
    session_id             = ReadOnlyProperty()
    advance_cluster_time   = DelegateMethod()
    advance_operation_time = DelegateMethod()

    def __init__(self, delegate, motor_client):
        AgnosticBase.__init__(self, delegate=delegate)
        self._client = motor_client

    def get_io_loop(self):
        return self._client.get_io_loop()

    def start_transaction(self, read_concern=None, write_concern=None,
                          read_preference=None, max_commit_time_ms=None):
        """Start a multi-statement transaction.

        Takes the same arguments as
        :class:`~pymongo.client_session.TransactionOptions`.

        Best used in a context manager block:

        .. code-block:: python3

          # Use "await" for start_session, but not for start_transaction.
          async with await client.start_session() as s:
              async with s.start_transaction():
                  await collection.delete_one({'x': 1}, session=s)
                  await collection.insert_one({'x': 2}, session=s)

        """
        self.delegate.start_transaction(read_concern=read_concern,
                                        write_concern=write_concern,
                                        read_preference=read_preference,
                                        max_commit_time_ms=max_commit_time_ms)
        return _MotorTransactionContext(self)

    @property
    def client(self):
        """The :class:`~MotorClient` this session was created from. """
        return self._client

    if PY35:
        exec(textwrap.dedent("""
        async def __aenter__(self):
            return self
    
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.delegate.__exit__(exc_type, exc_val, exc_tb)
        """), globals(), locals())

    def __enter__(self):
        raise AttributeError("Use Motor sessions like 'async with await"
                             " client.start_session()', not 'with'")

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AgnosticDatabase(AgnosticBaseProperties):
    __motor_class_name__ = 'MotorDatabase'
    __delegate_class__ = Database

    command               = AsyncCommand(doc=cmd_doc)
    create_collection     = AsyncCommand().wrap(Collection)
    current_op            = AsyncRead()
    dereference           = AsyncRead()
    drop_collection       = AsyncCommand().unwrap('MotorCollection')
    get_collection        = DelegateMethod().wrap(Collection)
    list_collection_names = AsyncRead()
    list_collections      = AsyncRead()
    name                  = ReadOnlyProperty()
    profiling_info        = AsyncRead()
    profiling_level       = AsyncRead()
    set_profiling_level   = AsyncCommand()
    validate_collection   = AsyncRead().unwrap('MotorCollection')

    incoming_manipulators         = ReadOnlyProperty()
    incoming_copying_manipulators = ReadOnlyProperty()
    outgoing_manipulators         = ReadOnlyProperty()
    outgoing_copying_manipulators = ReadOnlyProperty()

    def __init__(self, client, name, **kwargs):
        self._client = client
        delegate = kwargs.get('_delegate') or Database(
            client.delegate, name, **kwargs)

        super(self.__class__, self).__init__(delegate)

    def watch(self, pipeline=None, full_document='default', resume_after=None,
              max_await_time_ms=None, batch_size=None, collation=None,
              start_at_operation_time=None, session=None):
        """Watch changes on this database.

        Returns a :class:`~MotorChangeStream` cursor which iterates over changes
        on this database. Introduced in MongoDB 4.0.

        See the documentation for :meth:`MotorCollection.watch` for more
        details and examples.

        :Parameters:
          - `pipeline` (optional): A list of aggregation pipeline stages to
            append to an initial ``$changeStream`` stage. Not all
            pipeline stages are valid after a ``$changeStream`` stage, see the
            MongoDB documentation on change streams for the supported stages.
          - `full_document` (optional): The fullDocument option to pass
            to the ``$changeStream`` stage. Allowed values: 'default',
            'updateLookup'.  Defaults to 'default'.
            When set to 'updateLookup', the change notification for partial
            updates will include both a delta describing the changes to the
            document, as well as a copy of the entire document that was
            changed from some time after the change occurred.
          - `resume_after` (optional): The logical starting point for this
            change stream.
          - `max_await_time_ms` (optional): The maximum time in milliseconds
            for the server to wait for changes before responding to a getMore
            operation.
          - `batch_size` (optional): The maximum number of documents to return
            per batch.
          - `collation` (optional): The :class:`~pymongo.collation.Collation`
            to use for the aggregation.
          - `start_at_operation_time` (optional): If provided, the resulting
            change stream will only return changes that occurred at or after
            the specified :class:`~bson.timestamp.Timestamp`. Requires
            MongoDB >= 4.0.
          - `session` (optional): a
            :class:`~pymongo.client_session.ClientSession`.

        :Returns:
          A :class:`~MotorChangeStream`.

        .. versionadded:: 2.0

        .. mongodoc:: changeStreams
        """
        cursor_class = create_class_with_framework(
            AgnosticChangeStream, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, pipeline, full_document, resume_after,
                            max_await_time_ms, batch_size, collation,
                            start_at_operation_time, session)

    @property
    def client(self):
        """This MotorDatabase's :class:`MotorClient`."""
        return self._client

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
        client_class_name = self._client.__class__.__name__
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
        klass = create_class_with_framework(
            AgnosticCollection,
            self._framework,
            self.__module__)

        return klass(self, collection.name, _delegate=collection)

    def get_io_loop(self):
        return self._client.get_io_loop()


class AgnosticCollection(AgnosticBaseProperties):
    __motor_class_name__ = 'MotorCollection'
    __delegate_class__ = Collection

    bulk_write               = AsyncCommand(doc=bulk_write_doc)
    count_documents          = AsyncRead()
    create_index             = AsyncCommand()
    create_indexes           = AsyncCommand(doc=create_indexes_doc)
    delete_many              = AsyncCommand(doc=delete_many_doc)
    delete_one               = AsyncCommand(doc=delete_one_doc)
    distinct                 = AsyncRead()
    drop                     = AsyncCommand(doc=drop_doc)
    drop_index               = AsyncCommand()
    drop_indexes             = AsyncCommand()
    estimated_document_count = AsyncCommand()
    find_one                 = AsyncRead(doc=find_one_doc)
    find_one_and_delete      = AsyncCommand(doc=find_one_and_delete_doc)
    find_one_and_replace     = AsyncCommand(doc=find_one_and_replace_doc)
    find_one_and_update      = AsyncCommand(doc=find_one_and_update_doc)
    full_name                = ReadOnlyProperty()
    index_information        = AsyncRead(doc=index_information_doc)
    inline_map_reduce        = AsyncRead()
    insert_many              = AsyncWrite(doc=insert_many_doc)
    insert_one               = AsyncCommand(doc=insert_one_doc)
    map_reduce               = AsyncCommand(doc=mr_doc).wrap(Collection)
    name                     = ReadOnlyProperty()
    options                  = AsyncRead()
    reindex                  = AsyncCommand()
    rename                   = AsyncCommand()
    replace_one              = AsyncCommand(doc=replace_one_doc)
    update_many              = AsyncCommand(doc=update_many_doc)
    update_one               = AsyncCommand(doc=update_one_doc)
    with_options             = DelegateMethod().wrap(Collection)

    _async_aggregate             = AsyncRead(attr_name='aggregate')
    _async_aggregate_raw_batches = AsyncRead(attr_name='aggregate_raw_batches')
    _async_list_indexes          = AsyncRead(attr_name='list_indexes')

    def __init__(self, database, name, codec_options=None,
                 read_preference=None, write_concern=None, read_concern=None,
                 _delegate=None):
        db_class = create_class_with_framework(
            AgnosticDatabase, self._framework, self.__module__)

        if not isinstance(database, db_class):
            raise TypeError("First argument to MotorCollection must be "
                            "MotorDatabase, not %r" % database)

        delegate = _delegate or Collection(
            database.delegate, name, codec_options=codec_options,
            read_preference=read_preference, write_concern=write_concern,
            read_concern=read_concern)

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

        return collection_class(self.database, self.name + '.' + name,
                                _delegate=self.delegate[name])

    def __call__(self, *args, **kwargs):
        raise TypeError(
            "MotorCollection object is not callable. If you meant to "
            "call the '%s' method on a MotorCollection object it is "
            "failing because no such method exists." %
            self.delegate.name)

    def find(self, *args, **kwargs):
        """Create a :class:`MotorCursor`. Same parameters as for
        PyMongo's :meth:`~pymongo.collection.Collection.find`.

        Note that ``find`` does not require an ``await`` expression, because
        ``find`` merely creates a
        :class:`MotorCursor` without performing any operations on the server.
        ``MotorCursor`` methods such as :meth:`~MotorCursor.to_list`
        perform actual operations.
        """
        cursor = self.delegate.find(*unwrap_args_session(args),
                                    **unwrap_kwargs_session(kwargs))
        cursor_class = create_class_with_framework(
            AgnosticCursor, self._framework, self.__module__)

        return cursor_class(cursor, self)

    def find_raw_batches(self, *args, **kwargs):
        """Query the database and retrieve batches of raw BSON.

        Similar to the :meth:`find` method but returns each batch as bytes.

        This example demonstrates how to work with raw batches, but in practice
        raw batches should be passed to an external library that can decode
        BSON into another data type, rather than used with PyMongo's
        :mod:`bson` module.

        .. code-block:: python3

          async def get_raw():
              cursor = db.test.find_raw_batches()
              async for batch in cursor:
                  print(bson.decode_all(batch))

        Note that ``find_raw_batches`` does not support sessions.

        .. versionadded:: 2.0
        """
        cursor = self.delegate.find_raw_batches(*unwrap_args_session(args),
                                                **unwrap_kwargs_session(kwargs))
        cursor_class = create_class_with_framework(
            AgnosticRawBatchCursor, self._framework, self.__module__)

        return cursor_class(cursor, self)

    def aggregate(self, pipeline, **kwargs):
        """Execute an aggregation pipeline on this collection.

        The aggregation can be run on a secondary if the client is connected
        to a replica set and its ``read_preference`` is not :attr:`PRIMARY`.

        :Parameters:
          - `pipeline`: a single command or list of aggregation commands
          - `session` (optional): a
            :class:`~pymongo.client_session.ClientSession`, created with
            :meth:`~MotorClient.start_session`.
          - `**kwargs`: send arbitrary parameters to the aggregate command

        Returns a :class:`MotorCommandCursor` that can be iterated like a
        cursor from :meth:`find`::

          pipeline = [{'$project': {'name': {'$toUpper': '$name'}}}]
          cursor = collection.aggregate(pipeline)
          while (yield cursor.fetch_next):
              doc = cursor.next_object()
              print(doc)

        In Python 3.5 and newer, aggregation cursors can be iterated elegantly
        in native coroutines with `async for`::

          async def f():
              async for doc in collection.aggregate(pipeline):
                  print(doc)

        :class:`MotorCommandCursor` does not allow the ``explain`` option. To
        explain MongoDB's query plan for the aggregation, use
        :meth:`MotorDatabase.command`::

          async def f():
              plan = await db.command(
                  'aggregate', 'COLLECTION-NAME',
                  pipeline=[{'$project': {'x': 1}}],
                  explain=True)

              print(plan)

        .. versionchanged:: 1.0
           :meth:`aggregate` now **always** returns a cursor.

        .. versionchanged:: 0.5
           :meth:`aggregate` now returns a cursor by default,
           and the cursor is returned immediately without a ``yield``.
           See :ref:`aggregation changes in Motor 0.5 <aggregate_changes_0_5>`.

        .. versionchanged:: 0.2
           Added cursor support.

        .. _aggregate command:
            http://docs.mongodb.org/manual/applications/aggregation

        """
        cursor_class = create_class_with_framework(
            AgnosticLatentCommandCursor, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, self._async_aggregate, pipeline,
                            **unwrap_kwargs_session(kwargs))

    def aggregate_raw_batches(self, pipeline, **kwargs):
        """Perform an aggregation and retrieve batches of raw BSON.

        Similar to the :meth:`aggregate` method but returns each batch as bytes.

        This example demonstrates how to work with raw batches, but in practice
        raw batches should be passed to an external library that can decode
        BSON into another data type, rather than used with PyMongo's
        :mod:`bson` module.

        .. code-block:: python3

          async def get_raw():
              cursor = db.test.aggregate_raw_batches()
              async for batch in cursor:
                  print(bson.decode_all(batch))

        Note that ``aggregate_raw_batches`` does not support sessions.

        .. versionadded:: 2.0
        """
        cursor_class = create_class_with_framework(
            AgnosticLatentCommandCursor, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, self._async_aggregate_raw_batches, pipeline,
                            **unwrap_kwargs_session(kwargs))

    def watch(self, pipeline=None, full_document='default', resume_after=None,
              max_await_time_ms=None, batch_size=None, collation=None,
              start_at_operation_time=None, session=None):
        """Watch changes on this collection.

        Returns a :class:`~MotorChangeStream` cursor which iterates over changes
        on this collection. Introduced in MongoDB 3.6.

        A change stream continues waiting indefinitely for matching change
        events. Code like the following allows a program to cancel the change
        stream and exit.

        .. code-block:: python3

          change_stream = None

          async def watch_collection():
              global change_stream

              # Using the change stream in an "async with" block
              # ensures it is canceled promptly if your code breaks
              # from the loop or throws an exception.
              async with db.collection.watch() as change_stream:
                  async for change in change_stream:
                      print(change)

          # Tornado
          from tornado.ioloop import IOLoop

          def main():
              loop = IOLoop.current()
              # Start watching collection for changes.
              loop.add_callback(watch_collection)
              try:
                  loop.start()
              except KeyboardInterrupt:
                  pass
              finally:
                  if change_stream is not None:
                      change_stream.close()

          # asyncio
          from asyncio import get_event_loop

          def main():
              loop = get_event_loop()
              task = loop.create_task(watch_collection)

              try:
                  loop.run_forever()
              except KeyboardInterrupt:
                  pass
              finally:
                  if change_stream is not None:
                      change_stream.close()

                  # Prevent "Task was destroyed but it is pending!"
                  loop.run_until_complete(task)

        The :class:`~MotorChangeStream` async iterable blocks
        until the next change document is returned or an error is raised. If
        the :meth:`~MotorChangeStream.next` method encounters
        a network error when retrieving a batch from the server, it will
        automatically attempt to recreate the cursor such that no change
        events are missed. Any error encountered during the resume attempt
        indicates there may be an outage and will be raised.

        .. code-block:: python3

            try:
                pipeline = [{'$match': {'operationType': 'insert'}}]
                async with db.collection.watch(pipeline) as stream:
                    async for change in stream:
                        print(change)
            except pymongo.errors.PyMongoError:
                # The ChangeStream encountered an unrecoverable error or the
                # resume attempt failed to recreate the cursor.
                logging.error('...')

        For a precise description of the resume process see the
        `change streams specification`_.

        :Parameters:
          - `pipeline` (optional): A list of aggregation pipeline stages to
            append to an initial ``$changeStream`` stage. Not all
            pipeline stages are valid after a ``$changeStream`` stage, see the
            MongoDB documentation on change streams for the supported stages.
          - `full_document` (optional): The fullDocument option to pass
            to the ``$changeStream`` stage. Allowed values: 'default',
            'updateLookup'.  Defaults to 'default'.
            When set to 'updateLookup', the change notification for partial
            updates will include both a delta describing the changes to the
            document, as well as a copy of the entire document that was
            changed from some time after the change occurred.
          - `resume_after` (optional): The logical starting point for this
            change stream.
          - `max_await_time_ms` (optional): The maximum time in milliseconds
            for the server to wait for changes before responding to a getMore
            operation.
          - `batch_size` (optional): The maximum number of documents to return
            per batch.
          - `collation` (optional): The :class:`~pymongo.collation.Collation`
            to use for the aggregation.
          - `session` (optional): a
            :class:`~pymongo.client_session.ClientSession`.

        :Returns:
          A :class:`~MotorChangeStream`.

        See the :ref:`tornado_change_stream_example`.

        .. versionadded:: 1.2

        .. mongodoc:: changeStreams

        .. _change streams specification:
            https://github.com/mongodb/specifications/blob/master/source/change-streams.rst
        """
        cursor_class = create_class_with_framework(
            AgnosticChangeStream, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, pipeline, full_document, resume_after,
                            max_await_time_ms, batch_size, collation,
                            start_at_operation_time, session)

    def list_indexes(self, session=None):
        """Get a cursor over the index documents for this collection. ::

          async def print_indexes():
              async for index in db.test.list_indexes():
                  print(index)

        If the only index is the default index on ``_id``, this might print::

            SON([('v', 1), ('key', SON([('_id', 1)])), ('name', '_id_'), ('ns', 'test.test')])
        """
        cursor_class = create_class_with_framework(
            AgnosticLatentCommandCursor, self._framework, self.__module__)

        # Latent cursor that will send initial command on first "async for".
        return cursor_class(self, self._async_list_indexes, session=session)

    def wrap(self, obj):
        if obj.__class__ is Collection:
            # Replace pymongo.collection.Collection with MotorCollection.
            return self.__class__(self.database, obj.name, _delegate=obj)
        elif obj.__class__ is Cursor:
            return AgnosticCursor(obj, self)
        elif obj.__class__ is CommandCursor:
            command_cursor_class = create_class_with_framework(
                AgnosticCommandCursor,
                self._framework,
                self.__module__)

            return command_cursor_class(obj, self)
        elif obj.__class__ is ChangeStream:
            change_stream_class = create_class_with_framework(
                AgnosticChangeStream,
                self._framework,
                self.__module__)

            return change_stream_class(obj, self)
        else:
            return obj

    def get_io_loop(self):
        return self.database.get_io_loop()


class AgnosticBaseCursor(AgnosticBase):
    """Base class for AgnosticCursor and AgnosticCommandCursor"""
    _refresh      = AsyncRead()
    address       = ReadOnlyProperty()
    cursor_id     = ReadOnlyProperty()
    alive         = ReadOnlyProperty()
    session       = ReadOnlyProperty()

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

    # python.org/dev/peps/pep-0492/#api-design-and-implementation-revisions
    if PY35:
        exec(textwrap.dedent("""
        def __aiter__(self):
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

        .. doctest:: fetch_next
          :hide:

          >>> _ = MongoClient().test.test_collection.delete_many({})
          >>> collection = MotorClient().test.test_collection

        .. doctest:: fetch_next

          >>> @gen.coroutine
          ... def f():
          ...     yield collection.insert_many([{'_id': i} for i in range(5)])
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

        .. _`large batches`: https://docs.mongodb.com/manual/tutorial/iterate-a-cursor/#cursor-batches
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

        :meth:`each` returns immediately, and `callback` is executed asynchronously
        for each document. `callback` is passed ``(None, None)`` when iteration
        is complete.

        Cancel iteration early by returning ``False`` from the callback. (Only
        ``False`` cancels iteration: returning ``None`` or 0 does not.)

        .. testsetup:: each

          from tornado.ioloop import IOLoop
          MongoClient().test.test_collection.delete_many({})
          MongoClient().test.test_collection.insert_many(
              [{'_id': i} for i in range(5)])

          collection = MotorClient().test.test_collection

        .. doctest:: each

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
          >>> cursor = collection.find().sort([('_id', 1)])
          >>> cursor.each(callback=each)
          >>> IOLoop.current().start()
          0, 1, 2, 3, 4, done

        .. note:: Unlike other Motor methods, ``each`` requires a callback and
           does not return a Future, so it cannot be used in a coroutine.
           ``async for``, :meth:`to_list`, :attr:`fetch_next` are much easier to
           use.

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
    def to_list(self, length):
        """Get a list of documents.

        .. testsetup:: to_list

          MongoClient().test.test_collection.delete_many({})
          MongoClient().test.test_collection.insert_many([{'_id': i} for i in range(4)])

          from tornado import ioloop

        .. doctest:: to_list

          >>> from motor.motor_tornado import MotorClient
          >>> collection = MotorClient().test.test_collection
          >>>
          >>> @gen.coroutine
          ... def f():
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

         Returns a Future.

        .. versionchanged:: 2.0
           No longer accepts a callback argument.

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

        future = self._framework.get_future(self.get_io_loop())

        if not self.alive:
            future.set_result([])
        else:
            the_list = []
            self._framework.add_future(
                self.get_io_loop(),
                self._get_more(),
                self._to_list, length, the_list, future)

        return future

    def _to_list(self, length, the_list, future, get_more_result):
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
                future.set_result(the_list)
            else:
                self._framework.add_future(
                    self.get_io_loop(),
                    self._get_more(),
                    self._to_list, length, the_list, future)
        except Exception as exc:
            future.set_exception(exc)

    def get_io_loop(self):
        return self.collection.get_io_loop()

    @motor_coroutine
    def close(self):
        """Explicitly kill this cursor on the server. Call like (in Tornado):

        .. code-block:: python

            yield cursor.close()
        """
        if not self.closed:
            self.closed = True
            yield self._framework.yieldable(self._close())

    def batch_size(self, batch_size):
        self.delegate.batch_size(batch_size)
        return self

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
    address           = ReadOnlyProperty()
    collation         = MotorCursorChainingMethod()
    distinct          = AsyncRead()
    explain           = AsyncRead()
    add_option        = MotorCursorChainingMethod()
    remove_option     = MotorCursorChainingMethod()
    limit             = MotorCursorChainingMethod()
    skip              = MotorCursorChainingMethod()
    max_scan          = MotorCursorChainingMethod()
    sort              = MotorCursorChainingMethod(doc=cursor_sort_doc)
    hint              = MotorCursorChainingMethod()
    where             = MotorCursorChainingMethod()
    max_await_time_ms = MotorCursorChainingMethod()
    max_time_ms       = MotorCursorChainingMethod()
    min               = MotorCursorChainingMethod()
    max               = MotorCursorChainingMethod()
    comment           = MotorCursorChainingMethod()

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


class AgnosticRawBatchCursor(AgnosticCursor):
    __motor_class_name__ = 'MotorRawBatchCursor'
    __delegate_class__ = RawBatchCursor


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


class AgnosticRawBatchCommandCursor(AgnosticCommandCursor):
    __motor_class_name__ = 'MotorRawBatchCommandCursor'
    __delegate_class__ = RawBatchCommandCursor


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


class AgnosticLatentCommandCursor(AgnosticCommandCursor):
    __motor_class_name__ = 'MotorLatentCommandCursor'

    def __init__(self, collection, start, *args, **kwargs):
        # We're being constructed without yield or await, like:
        #
        #     cursor = collection.aggregate(pipeline)
        #
        # ... so we can't send the "aggregate" command to the server and get
        # a PyMongo CommandCursor back yet. Set self.delegate to a latent
        # cursor until the first yield or await triggers _get_more(), which
        # will execute the callback "start", which gets a PyMongo CommandCursor.
        super(self.__class__, self).__init__(_LatentCursor(), collection)
        self.start = start
        self.args = args
        self.kwargs = kwargs

    def batch_size(self, batch_size):
        self.kwargs['batchSize'] = batch_size
        return self

    def _get_more(self):
        if not self.started:
            self.started = True
            original_future = self._framework.get_future(self.get_io_loop())
            future = self.start(
                *self.args,
                **self.kwargs)

            self.start = self.args = self.kwargs = None

            self._framework.add_future(
                self.get_io_loop(),
                future,
                self._on_started, original_future)

            return original_future

        return super(self.__class__, self)._get_more()

    def _on_started(self, original_future, future):
        try:
            # "result" is a PyMongo command cursor from PyMongo's aggregate() or
            # aggregate_raw_batches(). Set its batch size from our latent
            # cursor's batch size.
            pymongo_cursor = future.result()
            self.delegate = pymongo_cursor
        except Exception as exc:
            original_future.set_exception(exc)
        else:
            if self.delegate._CommandCursor__data or not self.delegate.alive:
                # _get_more is complete.
                original_future.set_result(
                    len(self.delegate._CommandCursor__data))
            else:
                # Send a getMore.
                future = super(self.__class__, self)._get_more()
                self._framework.chain_future(future, original_future)


class AgnosticChangeStream(AgnosticBase):
    """A change stream cursor.

    Should not be called directly by application developers. See
    :meth:`~MotorCollection.watch` for example usage.

    .. versionadded: 1.2
    .. mongodoc:: changeStreams
    """
    __delegate_class__ = ChangeStream
    __motor_class_name__ = 'MotorChangeStream'

    _close = AsyncCommand(attr_name='close')

    def __init__(self, target, pipeline, full_document, resume_after,
                 max_await_time_ms, batch_size, collation,
                 start_at_operation_time, session):
        super(self.__class__, self).__init__(delegate=None)
        # The "target" object is a client, database, or collection.
        self._target = target
        self._kwargs = {'pipeline': pipeline,
                        'full_document': full_document,
                        'resume_after': resume_after,
                        'max_await_time_ms': max_await_time_ms,
                        'batch_size': batch_size,
                        'collation': collation,
                        'start_at_operation_time': start_at_operation_time,
                        'session': session}

    def _next(self):
        # This method is run on a thread.
        try:
            if not self.delegate:
                self.delegate = self._target.delegate.watch(**self._kwargs)

            return self.delegate.next()
        except StopIteration:
            raise StopAsyncIteration()

    @coroutine_annotation
    def next(self):
        """Advance the cursor.

        This method blocks until the next change document is returned or an
        unrecoverable error is raised.

        Raises :exc:`StopAsyncIteration` if this change stream is closed.

        You can iterate the change stream by calling
        ``await change_stream.next()`` repeatedly, or with an "async for" loop:

        .. code-block:: python3

          async for change in db.collection.watch():
              print(change)

        """
        loop = self.get_io_loop()
        return self._framework.run_on_executor(loop, self._next)

    @coroutine_annotation
    def close(self):
        """Close this change stream.

        Stops any "async for" loops using this change stream.
        """
        if self.delegate:
            return self._close()

        # Never started.
        future = self._framework.get_future(self.get_io_loop())
        future.set_result(None)
        return future

    if PY35:
        exec(textwrap.dedent("""
        def __aiter__(self):
            return self

        __anext__ = next

        async def __aenter__(self):
            return self
    
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.delegate:
                self.delegate.close() 
        """), globals(), locals())

    def get_io_loop(self):
        return self._target.get_io_loop()

    def __enter__(self):
        raise RuntimeError('Use a change stream in "async with", not "with"')

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
