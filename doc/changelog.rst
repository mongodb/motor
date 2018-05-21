Changelog
=========

.. currentmodule:: motor.motor_tornado

Motor 1.2.2
-----------

Motor 1.2.0 requires PyMongo 3.6 or later. The dependency was properly
documented, but not enforced in ``setup.py``. PyMongo 3.6 is now an install-time
requirement; thanks to Shane Harvey for the fix.

Motor 1.2.1
-----------

An asyncio application that created a Change Stream with
:meth:`MotorCollection.watch` and shut down while the Change Stream was open
would print several errors. I have rewritten :meth:`MotorChangeStream.next`
and some Motor internals to allow clean shutdown with asyncio.

Motor 1.2
---------

Motor 1.2 drops support for MongoDB 2.4 and adds support for MongoDB 3.6
features. It depends on PyMongo 3.6 or later. Motor continues to support MongoDB
2.6 and later.

Dropped support for Python 2.6 and 3.3. Motor continues to support Python 2.7,
and 3.4+.

Dropped support for Tornado 3. A recent version of Tornado 4 is required.

Dropped support for the `Python 3.5.0 and Python 3.5.1 "async for" protocol
<https://python.org/dev/peps/pep-0492/#api-design-and-implementation-revisions>`_.
Motor allows "async for" with cursors in Python 3.5.2 and later.

See the :ref:`Compatibility Matrix <compatibility-matrix>` for the relationships
among Motor, Python, Tornado, and MongoDB versions.

Added support for `aiohttp`_ 2.0 and later, and dropped older aiohttp versions.

Highlights include:

- New method :meth:`MotorCollection.watch` to acquire a Change Stream on a
  collection.
- New Session API to support causal consistency, see
  :meth:`MotorClient.start_session`.
- Support for array_filters in
  :meth:`~MotorCollection.update_one`,
  :meth:`~MotorCollection.update_many`,
  :meth:`~MotorCollection.find_one_and_update`,
  :meth:`~MotorCollection.bulk_write`.
- :meth:`MotorClient.list_databases` and :meth:`MotorClient.list_database_names`.
- Support for mongodb+srv:// URIs. See
  :class:`~pymongo.mongo_client.MongoClient` for details.
- Support for retryable writes and the ``retryWrites`` URI option.  See
  :class:`~pymongo.mongo_client.MongoClient` for details.

The maximum number of workers in the thread pool can be overridden with an
environment variable, see :doc:`configuration`.

:class:`MotorCollection` accepts codec_options, read_preference, write_concern,
and read_concern arguments. This is rarely needed; you typically create a
:class:`MotorCollection` from a :class:`MotorDatabase`, not by calling its
constructor directly.

Deleted obsolete class ``motor.Op``.

Motor 1.1
---------

Motor depends on PyMongo 3.4 or later. It wraps the latest PyMongo code which
support the new server features introduced in MongoDB 3.4. (It is a coincidence
that the latest MongoDB and PyMongo versions are the same number.)

Highlights include:

- Complete support for MongoDB 3.4:

  - Unicode aware string comparison using collations. See :ref:`PyMongo's examples for collation <collation-on-operation>`.
  - :class:`MotorCursor` and :class:`MotorGridOutCursor` have a new attribute :meth:`~MotorCursor.collation`.
  - Support for the new :class:`~bson.decimal128.Decimal128` BSON type.
  - A new maxStalenessSeconds read preference option.
  - A username is no longer required for the MONGODB-X509 authentication
    mechanism when connected to MongoDB >= 3.4.
  - :meth:`~MotorCollection.parallel_scan` supports maxTimeMS.
  - :class:`~pymongo.write_concern.WriteConcern` is automatically
    applied by all helpers for commands that write to the database when
    connected to MongoDB 3.4+. This change affects the following helpers:

    - :meth:`MotorClient.drop_database`
    - :meth:`MotorDatabase.create_collection`
    - :meth:`MotorDatabase.drop_collection`
    - :meth:`MotorCollection.aggregate` (when using $out)
    - :meth:`MotorCollection.create_indexes`
    - :meth:`MotorCollection.create_index`
    - :meth:`MotorCollection.drop_indexes`
    - :meth:`MotorCollection.drop_indexes`
    - :meth:`MotorCollection.drop_index`
    - :meth:`MotorCollection.map_reduce` (when output is not
      "inline")
    - :meth:`MotorCollection.reindex`
    - :meth:`MotorCollection.rename`

- Improved support for logging server discovery and monitoring events. See
  :mod:`PyMongo's monitoring documentation <pymongo.monitoring>` for examples.
- Support for matching iPAddress subjectAltName values for TLS certificate
  verification.
- TLS compression is now explicitly disabled when possible.
- The Server Name Indication (SNI) TLS extension is used when possible.
- PyMongo's `bson` module provides finer control over JSON encoding/decoding
  with :class:`~bson.json_util.JSONOptions`.
- Allow :class:`~bson.code.Code` objects to have a scope of ``None``,
  signifying no scope. Also allow encoding Code objects with an empty scope
  (i.e. ``{}``).

.. warning:: Starting in PyMongo 3.4, :attr:`bson.code.Code.scope` may return
  ``None``, as the default scope is ``None`` instead of ``{}``.

.. note:: PyMongo 3.4+ attempts to create sockets non-inheritable when possible
  (i.e. it sets the close-on-exec flag on socket file descriptors). Support
  is limited to a subset of POSIX operating systems (not including Windows) and
  the flag usually cannot be set in a single atomic operation. CPython 3.4+
  implements `PEP 446`_, creating all file descriptors non-inheritable by
  default. Users that require this behavior are encouraged to upgrade to
  CPython 3.4+.

.. _PEP 446: https://www.python.org/dev/peps/pep-0446/

Motor 1.0
---------

Motor now depends on PyMongo 3.3 and later. The move from PyMongo 2 to 3 brings
a large number of API changes, read :doc:`migrate-to-motor-1` and
`the PyMongo 3 changelog`_ carefully.

.. _the PyMongo 3 changelog: http://api.mongodb.com/python/current/changelog.html#changes-in-version-3-0

:class:`MotorReplicaSetClient` is removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In Motor 1.0, :class:`MotorClient` is the only class. Connect to a replica set with
a "replicaSet" URI option or parameter::

  MotorClient("mongodb://hostname/?replicaSet=my-rs")
  MotorClient(host, port, replicaSet="my-rs")

New features
~~~~~~~~~~~~

New classes :class:`~motor.motor_tornado.MotorGridFSBucket` and :class:`~motor.motor_asyncio.AsyncIOMotorGridFSBucket`
conform to the `GridFS API Spec <https://github.com/mongodb/specifications/blob/master/source/gridfs/gridfs-spec.rst>`_
for MongoDB drivers. These classes supersede the old
:class:`~motor.motor_tornado.MotorGridFS` and
:class:`~motor.motor_asyncio.AsyncIOMotorGridFS`. See `GridFS`_ changes below,
especially note the **breaking change** in
:class:`~motor.motor_web.GridFSHandler`.

Serve GridFS files over HTTP using `aiohttp`_ and
:class:`~motor.aiohttp.AIOHTTPGridFS`.

.. _aiohttp: https://aiohttp.readthedocs.io/

:class:`MotorClient` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Removed:

 - :meth:`MotorClient.open`; clients have opened themselves automatically on demand
   since version 0.2.
 - :attr:`MotorClient.seeds`, use :func:`pymongo.uri_parser.parse_uri` on your MongoDB URI.
 - :attr:`MotorClient.alive`

Added:

 - :attr:`MotorClient.event_listeners`
 - :attr:`MotorClient.max_idle_time_ms`
 - :attr:`MotorClient.min_pool_size`

Unix domain socket paths must be quoted with :func:`urllib.parse.quote_plus` (or
``urllib.quote_plus`` in Python 2) before they are included in a URI:

.. code-block:: python

    path = '/tmp/mongodb-27017.sock'
    MotorClient('mongodb://%s' % urllib.parse.quote_plus(path))

:class:`~motor.motor_tornado.MotorCollection` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Added:

 - :meth:`MotorCollection.create_indexes`
 - :meth:`MotorCollection.list_indexes`

New ``bypass_document_validation`` parameter for
:meth:`~.MotorCollection.initialize_ordered_bulk_op` and
:meth:`~.MotorCollection.initialize_unordered_bulk_op`.

Changes to :meth:`~motor.motor_tornado.MotorCollection.find` and :meth:`~motor.motor_tornado.MotorCollection.find_one`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following find/find_one options have been renamed:

These renames only affect your code if you passed these as keyword arguments,
like ``find(fields=['fieldname'])``. If you passed only positional parameters these
changes are not significant for your application.

- spec -> filter
- fields -> projection
- partial -> allow_partial_results

The following find/find_one options have been added:

- cursor_type (see :class:`~pymongo.cursor.CursorType` for values)
- oplog_replay
- modifiers

The following find/find_one options have been removed:

- network_timeout (use :meth:`~motor.motor_tornado.MotorCursor.max_time_ms` instead)
- read_preference (use :meth:`~motor.motor_tornado.MotorCollection.with_options`
  instead)
- tag_sets (use one of the read preference classes from
  :mod:`~pymongo.read_preferences` and
  :meth:`~motor.motor_tornado.MotorCollection.with_options` instead)
- secondary_acceptable_latency_ms (use the ``localThresholdMS`` URI option
  instead)
- max_scan (use the new ``modifiers`` option instead)
- snapshot (use the new ``modifiers`` option instead)
- tailable (use the new ``cursor_type`` option instead)
- await_data (use the new ``cursor_type`` option instead)
- exhaust (use the new ``cursor_type`` option instead)
- as_class (use :meth:`~motor.motor_tornado.MotorCollection.with_options` with
  :class:`~bson.codec_options.CodecOptions` instead)
- compile_re (BSON regular expressions are always decoded to
  :class:`~bson.regex.Regex`)

The following find/find_one options are deprecated:

- manipulate

The following renames need special handling.

- timeout -> no_cursor_timeout -
  By default, MongoDB closes a cursor after 10 minutes of inactivity. In previous
  Motor versions, you disabled the timeout by passing ``timeout=False`` to
  :meth:`.MotorCollection.find` or :meth:`.MotorGridFS.find`. The ``timeout``
  parameter has been renamed to ``no_cursor_timeout``, it defaults to ``False``,
  and you must now pass ``no_cursor_timeout=True`` to disable timeouts.

:class:`~motor.motor_tornado.MotorCursor`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Added:

 - :attr:`.MotorCursor.address`
 - :meth:`.MotorCursor.max_await_time_ms`

Removed:

 - :attr:`.MotorCursor.conn_id`, use :attr:`~.MotorCursor.address`

GridFS
~~~~~~

The old GridFS classes :class:`~motor.motor_tornado.MotorGridFS` and
:class:`~motor.motor_asyncio.AsyncIOMotorGridFS` are deprecated in favor of
:class:`~motor.motor_tornado.MotorGridFSBucket` and :class:`~motor.motor_asyncio.AsyncIOMotorGridFSBucket`,
which comply with MongoDB's cross-language driver spec for GridFS.

The old classes are still supported, but will be removed in Motor 2.0.

**BREAKING CHANGE**: The overridable method
:class:`~motor.web.GridFSHandler.get_gridfs_file` of
:class:`~motor.web.GridFSHandler` now takes a
:class:`~motor.motor_tornado.MotorGridFSBucket`, not a
:class:`~motor.motor_tornado.MotorGridFS`.
It also takes an additional ``request`` parameter.

:class:`~motor.motor_tornado.MotorGridOutCursor`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Added:

 - :attr:`.MotorGridOutCursor.address`
 - :meth:`.MotorGridOutCursor.max_await_time_ms`

Removed:

 - :attr:`.MotorGridOutCursor.conn_id`, use :attr:`~.MotorGridOutCursor.address`

:class:`~motor.motor_tornado.MotorGridIn`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New method :meth:`.MotorGridIn.abort`.

In a Python 3.5 native coroutine, the "async with" statement calls
:meth:`~MotorGridIn.close` automatically::

  async def upload():
      my_db = MotorClient().test
      fs = MotorGridFSBucket(my_db)
      async with await fs.new_file() as gridin:
          await gridin.write(b'First part\n')
          await gridin.write(b'Second part')

      # gridin is now closed automatically.

:class:`~motor.motor_tornado.MotorGridOut`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~motor.motor_tornado.MotorGridOut` is now an async iterable, so
reading a chunk at a time is much simpler with a Python 3 native coroutine::

    async def read_file(file_id):
        fs = motor.motor_tornado.MotorGridFS(db)
        gridout = await fs.get(file_id)

        async for chunk in gridout:
            sys.stdout.write(chunk)

        sys.stdout.flush()

Documentation
~~~~~~~~~~~~~

The :doc:`/api-asyncio/index` is now fully documented, side by side with the
:doc:`/api-tornado/index`.

New :doc:`developer-guide` added.

Motor 0.7
---------

For asynchronous I/O Motor now uses a thread pool, which is faster and simpler
than the prior implementation with greenlets. It no longer requires the
``greenlet`` package, and now requires the ``futures`` backport package on
Python 2.

This version updates the PyMongo dependency from 2.8.0 to 2.9.x, and wraps
PyMongo 2.9's new APIs.

Most of Motor 1.0's API is now implemented, and APIs that will be removed in
Motor 1.0 are now deprecated and raise warnings. See the
:doc:`/migrate-to-motor-1` to prepare your code for Motor 1.0.

:class:`MotorClient` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`~MotorClient.get_database` method is added for getting a :class:`MotorDatabase`
instance with its options configured differently than the MotorClient's.

New read-only attributes:

- :attr:`~MotorClient.codec_options`
- :attr:`~MotorClient.local_threshold_ms`
- :attr:`~MotorClient.max_write_batch_size`

:class:`MotorReplicaSetClient` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :meth:`~MotorReplicaSetClient.get_database` method is added for getting a
:class:`MotorDatabase` instance with its options configured differently than the
MotorReplicaSetClient's.

New read-only attributes:

- :attr:`~MotorReplicaSetClient.codec_options`
- :attr:`~MotorReplicaSetClient.local_threshold_ms`

:class:`MotorDatabase` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :meth:`~MotorDatabase.get_collection` method is added for getting a
:class:`MotorCollection` instance with its options configured differently than the
MotorDatabase's.

The ``connection`` property is deprecated in favor of a new read-only attribute
:attr:`~MotorDatabase.client`.

New read-only attribute:

- :attr:`~MotorDatabase.codec_options`

:class:`MotorCollection` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :meth:`~MotorCollection.with_options` method is added for getting a
:class:`MotorCollection` instance with its options configured differently than this
MotorCollection's.

New read-only attribute:

- :attr:`~MotorCollection.codec_options`

The following methods wrap PyMongo's implementation of the standard `CRUD API Spec`_
for MongoDB Drivers:

- :meth:`~MotorCollection.bulk_write`
- :meth:`~MotorCollection.insert_one`
- :meth:`~MotorCollection.insert_many`
- :meth:`~MotorCollection.update_one`
- :meth:`~MotorCollection.update_many`
- :meth:`~MotorCollection.replace_one`
- :meth:`~MotorCollection.delete_one`
- :meth:`~MotorCollection.delete_many`
- :meth:`~MotorCollection.find_one_and_delete`
- :meth:`~MotorCollection.find_one_and_replace`
- :meth:`~MotorCollection.find_one_and_update`

These new methods do not apply SON Manipulators.

.. _CRUD API Spec: https://github.com/mongodb/specifications/blob/master/source/crud/crud.rst

:doc:`GridFS <api-tornado/gridfs>` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New :class:`MotorGridOutCursor` methods:

- :meth:`~MotorGridOutCursor.add_option`
- :meth:`~MotorGridOutCursor.remove_option`
- :meth:`~MotorGridOutCursor.clone`

Added :class:`MotorGridOut` documentation:

- :attr:`~MotorGridOut.aliases`
- :attr:`~MotorGridOut.chunk_size`
- :meth:`~MotorGridOut.close`
- :attr:`~MotorGridOut.content_type`
- :attr:`~MotorGridOut.filename`
- :attr:`~MotorGridOut.length`
- :attr:`~MotorGridOut.md5`
- :attr:`~MotorGridOut.metadata`
- :attr:`~MotorGridOut.name`
- :attr:`~MotorGridOut.upload_date`

Bugfix
~~~~~~

`MOTOR-124 <https://jira.mongodb.org/browse/MOTOR-124>`_: an import deadlock
in Python 2 and Tornado 3 led to an :exc:`~pymongo.errors.AutoReconnect`
exception with some replica sets.

Motor 0.6.2
-----------

Fix "from motor import \*" for Python 3.

Motor 0.6.1
-----------

Fix source distribution, which hadn't included the "frameworks" submodules.

Motor 0.6
---------

This is a bugfix release. Fixing these bugs has introduced tiny API changes that
may affect some programs.

`motor_asyncio` and `motor_tornado` submodules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These modules have been moved from:

  - `motor_asyncio.py`
  - `motor_tornado.py`

To:

  - `motor_asyncio/__init__.py`
  - `motor_tornado/__init__.py`

Motor had to make this change in order to omit the `motor_asyncio` submodule
entirely and avoid a spurious :exc:`SyntaxError` being printed when installing in
Python 2. The change should be invisible to application code.

Database and collection names with leading underscores
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A database or collection whose name starts with an underscore can no longer be
accessed as a property::

    # Now raises AttributeError.
    db = MotorClient()._mydatabase
    collection = db._mycollection
    subcollection = collection._subcollection

Such databases and collections can still be accessed dict-style::

    # Continues to work the same as previous Motor versions.
    db = MotorClient()['_mydatabase']
    collection = db['_mycollection']

To ensure a "sub-collection" with a name that includes an underscore is
accessible, Motor collections now allow dict-style access, the same as Motor
clients and databases always have::

    # New in Motor 0.6
    subcollection = collection['_subcollection']    

These changes solve problems with iPython code completion and the Python 3
:class:`ABC` abstract base class.

Motor 0.5
---------

asyncio
~~~~~~~

Motor can now integrate with asyncio, as an alternative to Tornado. My gratitude
to Rémi Jolin, Andrew Svetlov, and Nikolay Novik for their huge contributions to
Motor's asyncio integration.

Python 3.5
~~~~~~~~~~

Motor is now compatible with Python 3.5, which required some effort.
Motor not only supports users' coroutines, it uses coroutines to implement
some of its own features, like :meth:`~MotorClient.open` and :meth:`~MotorGridFS.put`.
There is no single way to return a value from a Python 3.5 native coroutine
or a Python 2 generator-based coroutine, so Motor internal coroutines that
return values were rewritten. (See `commit message dc19418c`_ for an
explanation.)

.. _commit message dc19418c: https://github.com/mongodb/motor/commit/dc19418c

`async` and `await`
~~~~~~~~~~~~~~~~~~~

Motor now supports Python 3.5 native coroutines, written with the `async` and
`await` syntax::

    async def f():
        await collection.insert({'_id': 1})

Cursors from :meth:`~MotorCollection.find`, :meth:`~MotorCollection.aggregate`, or
:meth:`~MotorGridFS.find` can be iterated elegantly and very efficiently in native
coroutines with `async for`::

    async def f():
        async for doc in collection.find():
            do_something_with(doc)

.. _aggregate_changes_0_5:

:meth:`~MotorCollection.aggregate`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`MotorCollection.aggregate` now returns a cursor by default, and the cursor
is returned immediately without a `yield`. The old syntax is no longer
supported::

    # Motor 0.4 and older, no longer supported.
    cursor = yield collection.aggregate(pipeline, cursor={})
    while (yield cursor.fetch_next):
        doc = cursor.next_object()
        print(doc)

In Motor 0.5, simply do::

    # Motor 0.5: no "cursor={}", no "yield".
    cursor = collection.aggregate(pipeline)
    while (yield cursor.fetch_next):
        doc = cursor.next_object()
        print(doc)

Or with Python 3.5 and later::

    # Motor 0.5, Python 3.5.
    async for doc in collection.aggregate(pipeline):
        print(doc)

MongoDB versions 2.4 and older do not support aggregation cursors. For
compatibility with older MongoDBs, :meth:`~MotorCollection.aggregate` now takes an
argument ``cursor=False``, and returns a Future that you can yield to get all
the results in one document::

    # Motor 0.5 with MongoDB 2.4 and older.
    reply = yield collection.aggregate(cursor=False)
    for doc in reply['results']:
        print(doc)

Deprecations
~~~~~~~~~~~~

Motor 0.5 deprecates a large number of APIs that will be removed in version 1.0:

  `MotorClient`:
    - `~MotorClient.host`
    - `~MotorClient.port`
    - `~MotorClient.document_class`
    - `~MotorClient.tz_aware`
    - `~MotorClient.secondary_acceptable_latency_ms`
    - `~MotorClient.tag_sets`
    - `~MotorClient.uuid_subtype`
    - `~MotorClient.disconnect`
    - `~MotorClient.alive`

  `MotorReplicaSetClient`:
    - `~MotorReplicaSetClient.document_class`
    - `~MotorReplicaSetClient.tz_aware`
    - `~MotorReplicaSetClient.secondary_acceptable_latency_ms`
    - `~MotorReplicaSetClient.tag_sets`
    - `~MotorReplicaSetClient.uuid_subtype`
    - `~MotorReplicaSetClient.alive`

  `MotorDatabase`:
    - `~MotorDatabase.secondary_acceptable_latency_ms`
    - `~MotorDatabase.tag_sets`
    - `~MotorDatabase.uuid_subtype`

  `MotorCollection`:
    - `~MotorCollection.secondary_acceptable_latency_ms`
    - `~MotorCollection.tag_sets`
    - `~MotorCollection.uuid_subtype`

Cursor slicing
~~~~~~~~~~~~~~

Cursors can no longer be indexed like ``cursor[n]`` or sliced like
``cursor[start:end]``, see `MOTOR-84 <https://jira.mongodb.org/browse/MOTOR-84>`_.
If you wrote code like this::

    cursor = collection.find()[i]
    yield cursor.fetch_next
    doc = cursor.next_object()

Then instead, write::

    cursor = collection.find().skip(i).limit(-1)
    yield cursor.fetch_next
    doc = cursor.next_object()

The negative limit ensures the server closes the cursor after one result,
saving Motor the work of closing it. See `cursor.limit
<http://docs.mongodb.org/v3.0/reference/method/cursor.limit/>`_.

SSL hostname validation error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you use Motor with Tornado and SSL hostname validation fails, Motor used
to raise a :exc:`~pymongo.errors.ConnectionFailure` with a useful messsage like "hostname 'X'
doesn't match 'Y'". The message is now empty and Tornado logs a warning
instead.

Configuring uuid_subtype
~~~~~~~~~~~~~~~~~~~~~~~~

You can now get and set :attr:`~MotorClient.uuid_subtype` on :class:`MotorClient`,
:class:`MotorReplicaSetClient`, and :class:`MotorDatabase` instances, not just on
:class:`MotorCollection`.

Motor 0.4.1
-----------

Fix `MOTOR-66 <https://jira.mongodb.org/browse/MOTOR-66>`_, deadlock when
initiating :class:`MotorReplicaSetClient` connection from multiple operations
at once.

Motor 0.4
---------

Supports MongoDB 3.0. In particular, supports MongoDB 3.0's new SCRAM-SHA-1
authentication mechanism and updates the implementations of
:meth:`MotorClient.database_names` and :meth:`MotorDatabase.collection_names`.

Updates PyMongo dependency from 2.7.1 to 2.8,
therefore inheriting
`PyMongo 2.7.2's bug fixes <https://jira.mongodb.org/browse/PYTHON/fixforversion/14005>`_
and
`PyMongo 2.8's bug fixes <https://jira.mongodb.org/browse/PYTHON/fixforversion/14223>`_
and `features
<http://api.mongodb.org/python/current/changelog.html#changes-in-version-2-8>`_.

Fixes `a connection-pool timeout when waitQueueMultipleMS is set
<https://jira.mongodb.org/browse/MOTOR-62>`_ and `two bugs in replica set
monitoring <https://jira.mongodb.org/browse/MOTOR-61>`_.

The ``copy_database`` method has been removed. It was overly complex and no one
used it, see `MOTOR-56 <https://jira.mongodb.org/browse/MOTOR-56>`_.
You can still use the :meth:`MotorDatabase.command` method directly.
The only scenario not supported is copying a database from one host to
another, if the remote host requires authentication.
For this, use PyMongo's `copy_database`_ method, or, since PyMongo's
``copy_database`` will be removed in a future release too, use the mongo shell.

.. _copy_database: http://api.mongodb.org/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient.copy_database

.. seealso:: `The "copydb" command <http://docs.mongodb.org/manual/reference/command/copydb/>`_.

Motor 0.3.3
-----------

Fix `MOTOR-45 <https://jira.mongodb.org/browse/MOTOR-45>`_,
a stack-context leak in domain name resolution that could lead to an infinite
loop and rapid memory leak.

Document Motor's :doc:`requirements` in detail.

Motor 0.3.2
-----------

Fix `MOTOR-44 <https://jira.mongodb.org/browse/MOTOR-44>`_,
a socket leak in :class:`MotorClient.copy_database`
and :class:`MotorReplicaSetClient.copy_database`.

Motor 0.3.1
-----------

Fix `MOTOR-43 <https://jira.mongodb.org/browse/MOTOR-43>`_,
a TypeError when using :class:`~motor.web.GridFSHandler`
with a timezone-aware :class:`~motor.motor_tornado.MotorClient`.

Fix GridFS examples that hadn't been updated for Motor 0.2's new syntax.

Fix a unittest that hadn't been running.

Motor 0.3
---------

No new features.

* Updates PyMongo dependency from 2.7 to 2.7.1,
  therefore inheriting `PyMongo 2.7.1's bug fixes
  <https://jira.mongodb.org/browse/PYTHON/fixforversion/13823>`_.
* Motor continues to support Python 2.6, 2.7, 3.3, and 3.4,
  but now with single-source.
  2to3 no longer runs during installation with Python 3.
* ``nosetests`` is no longer required for regular Motor tests.
* Fixes `a mistake in the docstring <https://jira.mongodb.org/browse/MOTOR-34>`_
  for aggregate().

Motor 0.2.1
-----------

Fixes two bugs:

* `MOTOR-32 <https://jira.mongodb.org/browse/MOTOR-32>`_:
  The documentation for :meth:`MotorCursor.close` claimed it immediately
  halted execution of :meth:`MotorCursor.each`, but it didn't.
* `MOTOR-33 <https://jira.mongodb.org/browse/MOTOR-33>`_:
  An incompletely iterated cursor's ``__del__`` method sometimes got stuck
  and cost 100% CPU forever, even though the application was still responsive.

Motor 0.2
---------

This version includes API changes that break backward compatibility
with applications written for Motor 0.1. For most applications, the migration
chores will be minor. In exchange, Motor 0.2 offers a cleaner style, and
it wraps the new and improved PyMongo 2.7 instead of 2.5.

Changes in Dependencies
~~~~~~~~~~~~~~~~~~~~~~~

Motor now requires PyMongo 2.7.0 exactly and Tornado 3 or later. It drops
support for Python 2.5 since Tornado 3 has dropped it.

Motor continues to work with Python 2.6 through 3.4. It still requires
`Greenlet`_.

API Changes
~~~~~~~~~~~

open_sync
'''''''''

The ``open_sync`` method has been removed from :class:`MotorClient` and
:class:`MotorReplicaSetClient`. Clients now connect to MongoDB automatically on
first use. Simply delete the call to ``open_sync`` from your application.

If it's important to test that MongoDB is available before continuing
your application's startup, use ``IOLoop.run_sync``::

    loop = tornado.ioloop.IOLoop.current()
    client = motor.MotorClient(host, port)
    try:
        loop.run_sync(client.open)
    except pymongo.errors.ConnectionFailure:
        print "Can't connect"

Similarly, calling :meth:`MotorGridOut.open` is now optional.
:class:`MotorGridIn` and :class:`MotorGridFS` no longer have an ``open``
method at all.

.. _changelog-futures:

Futures
'''''''

Motor 0.2 takes advantage of Tornado's tidy new coroutine syntax::

    # Old style:
    document = yield motor.Op(collection.find_one, {'_id': my_id})

    # New style:
    document = yield collection.find_one({'_id': my_id})

To make this possible, Motor asynchronous methods
(except :meth:`MotorCursor.each`) now return a
:class:`~tornado.concurrent.Future`.

Using Motor with callbacks is still possible: If a callback is passed, it will
be executed with the ``(result, error)`` of the operation, same as in Motor
0.1::

    def callback(document, error):
        if error:
            logging.error("Oh no!")
        else:
            print document

    collection.find_one({'_id': my_id}, callback=callback)

If no callback is passed, a Future is returned that resolves to the
method's result or error::

    document = yield collection.find_one({'_id': my_id})

``motor.Op`` works the same as before, but it's deprecated.

``WaitOp`` and ``WaitAllOps`` have been removed. Code that used them can now
yield a ``Future`` or a list of them. Consider this function written for
Tornado 2 and Motor 0.1::

    @gen.engine
    def get_some_documents():
        cursor = collection.find().sort('_id').limit(2)
        cursor.to_list(callback=(yield gen.Callback('key')))
        do_something_while_we_wait()
        try:
            documents = yield motor.WaitOp('key')
            print documents
        except Exception, e:
            print e

The function now becomes::

    @gen.coroutine
    def f():
        cursor = collection.find().sort('_id').limit(2)
        future = cursor.to_list(2)
        do_something_while_we_wait()
        try:
            documents = yield future
            print documents
        except Exception, e:
            print e

Similarly, a function written like so in the old style::

    @gen.engine
    def get_two_documents_in_parallel(collection):
        collection.find_one(
            {'_id': 1}, callback=(yield gen.Callback('one')))

        collection.find_one(
            {'_id': 2}, callback=(yield gen.Callback('two')))

        try:
            doc_one, doc_two = yield motor.WaitAllOps(['one', 'two'])
            print doc_one, doc_two
        except Exception, e:
            print e

Now becomes::

    @gen.coroutine
    def get_two_documents_in_parallel(collection):
        future_0 = collection.find_one({'_id': 1})
        future_1 = collection.find_one({'_id': 2})

        try:
            doc_one, doc_two = yield [future_0, future_1]
            print doc_one, doc_two
        except Exception, e:
            print e


to_list
'''''''

Any calls to :meth:`MotorCursor.to_list` that omitted the ``length``
argument must now include it::

    result = yield collection.find().to_list(100)

``None`` is acceptable, meaning "unlimited." Use with caution.

Connection Pooling
''''''''''''''''''

:class:`MotorPool` has been rewritten. It supports the new options
introduced in PyMongo 2.6, and drops all Motor-specific options.

:class:`MotorClient` and :class:`MotorReplicaSetClient` have an option
``max_pool_size``. It used to mean "minimum idle sockets to keep open", but its
meaning has changed to "maximum sockets open per host." Once this limit is
reached, operations will pause waiting for a socket to become available.
Therefore the default has been raised from 10 to 100. If you pass a value for
``max_pool_size`` make sure it's large enough for the expected load. (Sockets
are only opened when needed, so there's no cost to having a ``max_pool_size``
larger than necessary. Err towards a larger value.) If you've been accepting
the default, continue to do so.

``max_pool_size`` is now synonymous with Motor's special ``max_concurrent``
option, so ``max_concurrent`` has been removed.

``max_wait_time`` has been renamed ``waitQueueTimeoutMS`` for consistency with
PyMongo. If you pass ``max_wait_time``, rename it and multiply by 1000.

The :exc:`MotorPoolTimeout` exception is gone; catch PyMongo's
:exc:`~pymongo.errors.ConnectionFailure` instead.

DNS
'''

Motor can take advantage of Tornado 3's `asynchronous resolver interface`_. By
default, Motor still uses blocking DNS, but you can enable non-blocking
lookup with a threaded resolver::

    Resolver.configure('tornado.netutil.ThreadedResolver')

Or install `pycares`_ and use the c-ares resolver::

    Resolver.configure('tornado.platform.caresresolver.CaresResolver')

MotorCursor.tail
''''''''''''''''

The ``MotorCursor.tail`` method has been removed. It was complex, diverged from
PyMongo's feature set, and encouraged overuse of MongoDB capped collections as
message queues when a purpose-built message queue is more appropriate. An
example of tailing a capped collection is provided instead:
:doc:`examples/tailable-cursors`.

MotorClient.is_locked
'''''''''''''''''''''

``is_locked`` has been removed since calling it from Motor would be
bizarre. If you called ``MotorClient.is_locked`` like::

    locked = yield motor.Op(client.is_locked)

you should now do::

    result = yield client.admin.current_op()
    locked = bool(result.get('fsyncLock', None))

The result is ``True`` only if an administrator has called `fsyncLock`_ on the
mongod. It is unlikely that you have any use for this.

GridFSHandler
'''''''''''''

:meth:`~web.GridFSHandler.get_gridfs_file` now
returns a Future instead of accepting a callback.

.. _Greenlet: http://pypi.python.org/pypi/greenlet/
.. _asynchronous resolver interface: http://www.tornadoweb.org/en/stable/netutil.html#tornado.netutil.Resolver
.. _pycares: https://pypi.python.org/pypi/pycares
.. _fsyncLock: http://docs.mongodb.org/manual/reference/method/db.fsyncLock/

New Features
~~~~~~~~~~~~

The introduction of a :ref:`Futures-based API <changelog-futures>` is the most
pervasive new feature. In addition Motor 0.2 includes new features from
PyMongo 2.6 and 2.7:

* :meth:`MotorCollection.aggregate` can return a cursor.
* Support for all current MongoDB authentication mechanisms (see PyMongo's
  `authentication examples`_).
* A new :meth:`MotorCollection.parallel_scan` method.
* An :doc:`API for bulk writes <examples/bulk>`.
* Support for wire protocol changes in MongoDB 2.6.
* The ability to specify a server-side timeout for operations
  with :meth:`~MotorCursor.max_time_ms`.
* A new :meth:`MotorGridFS.find` method for querying GridFS.

.. _authentication examples: http://api.mongodb.org/python/current/examples/authentication.html

Bugfixes
~~~~~~~~

``MotorReplicaSetClient.open`` threw an error if called without a callback.

``MotorCursor.to_list`` `ignored SON manipulators
<https://jira.mongodb.org/browse/MOTOR-8>`_. (Thanks to Eren Güven for the
report and the fix.)

`The full list is in Jira
<https://jira.mongodb.org/browse/MOTOR-23?filter=15038>`_.

Motor 0.1.2
-----------

Fixes innocuous unittest failures when running against Tornado 3.1.1.

Motor 0.1.1
-----------

Fixes issue `MOTOR-12`_ by pinning its PyMongo dependency to PyMongo version
2.5.0 exactly.

Motor relies on some of PyMongo's internal details, so changes to PyMongo can
break Motor, and a change in PyMongo 2.5.1 did. Eventually PyMongo will expose
stable hooks for Motor to use, but for now I changed Motor's dependency from
``PyMongo>=2.4.2`` to ``PyMongo==2.5.0``.

.. _MOTOR-12: https://jira.mongodb.org/browse/MOTOR-12
