Changelog
=========

.. currentmodule:: motor.motor_tornado

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

`MotorClient` changes
~~~~~~~~~~~~~~~~~~~~~

The `~MotorClient.get_database` method is added for getting a `MotorDatabase`
instance with its options configured differently than the MotorClient's.

New read-only attributes:

- `~MotorClient.codec_options`
- `~MotorClient.local_threshold_ms`
- `~MotorClient.max_write_batch_size`

`MotorReplicaSetClient` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `~MotorReplicaSetClient.get_database` method is added for getting a
`MotorDatabase` instance with its options configured differently than the
MotorReplicaSetClient's.

New read-only attributes:

- `~MotorReplicaSetClient.codec_options`
- `~MotorReplicaSetClient.local_threshold_ms`

`MotorDatabase` changes
~~~~~~~~~~~~~~~~~~~~~~~

The `~MotorDatabase.get_collection` method is added for getting a
`MotorCollection` instance with its options configured differently than the
MotorDatabase's.

The ``connection`` property is deprecated in favor of a new read-only attribute
`~MotorDatabase.client`.

New read-only attribute:

- `~MotorDatabase.codec_options`

`MotorCollection` changes
~~~~~~~~~~~~~~~~~~~~~~~~~

The `~MotorCollection.with_options` method is added for getting a
`MotorCollection` instance with its options configured differently than this
MotorCollection's.

New read-only attribute:

- `~MotorCollection.codec_options`

The following methods wrap PyMongo's implementation of the standard `CRUD API Spec`_
for MongoDB Drivers:

- `~MotorCollection.bulk_write`
- `~MotorCollection.insert_one`
- `~MotorCollection.insert_many`
- `~MotorCollection.update_one`
- `~MotorCollection.update_many`
- `~MotorCollection.replace_one`
- `~MotorCollection.delete_one`
- `~MotorCollection.delete_many`
- `~MotorCollection.find_one_and_delete`
- `~MotorCollection.find_one_and_replace`
- `~MotorCollection.find_one_and_update`

These new methods do not apply SON Manipulators.

.. _CRUD API Spec: https://github.com/mongodb/specifications/blob/master/source/crud/crud.rst

:doc:`GridFS <api/gridfs>` changes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

New `MotorGridOutCursor` methods:

- `~MotorGridOutCursor.add_option`
- `~MotorGridOutCursor.remove_option`
- `~MotorGridOutCursor.clone`

Added `MotorGridOut` documentation:

- `~MotorGridOut.aliases`
- `~MotorGridOut.chunk_size`
- `~MotorGridOut.close`
- `~MotorGridOut.content_type`
- `~MotorGridOut.filename`
- `~MotorGridOut.length`
- `~MotorGridOut.md5`
- `~MotorGridOut.metadata`
- `~MotorGridOut.name`
- `~MotorGridOut.upload_date`

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
entirely and avoid a spurious `SyntaxError` being printed when installing in
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
`ABC` abstract base class.

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
some of its own features, like `MotorClient.open` and `MotorGridFS.put`.
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

Cursors from `~MotorCollection.find`, `~MotorCollection.aggregate`, or
`MotorGridFS.find` can be iterated elegantly and very efficiently in native
coroutines with `async for`::

    async def f():
        async for doc in collection.find():
            do_something_with(doc)

.. _aggregate_changes_0_5:

`aggregate`
~~~~~~~~~~~

`MotorCollection.aggregate` now returns a cursor by default, and the cursor
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
compatibility with older MongoDBs, `~MotorCollection.aggregate` now takes an
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
to raise a `ConnectionFailure` with a useful messsage like "hostname 'X'
doesn't match 'Y'". The message is now empty and Tornado logs a warning
instead.

Configuring uuid_subtype
~~~~~~~~~~~~~~~~~~~~~~~~

You can now get and set `~MotorClient.uuid_subtype` on `MotorClient`,
`MotorReplicaSetClient`, and `MotorDatabase` instances, not just on
`MotorCollection`.

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
* `nosetests` is no longer required for regular Motor tests.
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
