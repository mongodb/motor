.. currentmodule:: motor.motor_tornado

=====================================
Differences between Motor and PyMongo
=====================================

.. important:: This page describes using Motor with Tornado. Beginning in
  version 0.5 Motor can also integrate with asyncio instead of Tornado. The
  documentation is not yet updated for Motor's asyncio integration.

Major differences
=================

Connecting to MongoDB
---------------------

PyMongo's connection classes are called
:class:`~pymongo.mongo_client.MongoClient` and
:class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient`.
Motor provides a `MotorClient` and `MotorReplicaSetClient`.

Motor's client classes do no I/O in their constructors; they connect
on demand, when you first attempt an operation.

Callbacks and Futures
---------------------

Motor supports nearly every method PyMongo does, but Motor methods that
do network I/O take an optional callback function. The callback must accept two
parameters:

.. code-block:: python

    def callback(result, error):
        pass

Motor's asynchronous methods return immediately, and execute the
callback, with either a result or an error, when the operation has completed.
For example, :meth:`~pymongo.collection.Collection.find_one` is used in PyMongo
like:

.. code-block:: python

    db = MongoClient().test
    user = db.users.find_one({'name': 'Jesse'})
    print user

But Motor's `MotorCollection.find_one` method is asynchronous:

.. code-block:: python

    db = MotorClient().test

    def got_user(user, error):
        if error:
            print 'error getting user!', error
        else:
            print user

    db.users.find_one({'name': 'Jesse'}, callback=got_user)

The callback must be passed as a keyword argument, not a positional argument.

To find multiple documents, Motor provides `MotorCursor.to_list`:

.. code-block:: python

    def got_users(users, error):
        if error:
            print 'error getting users!', error
        else:
            for user in users:
                print user

    db.users.find().to_list(length=10, callback=got_users)

.. seealso:: `MotorCursor.fetch_next`

If you pass no callback to an asynchronous method, it returns a Future for use
in a :func:`coroutine <tornado.gen.coroutine>`:

.. code-block:: python

    from tornado import gen

    @gen.coroutine
    def f():
        yield motor_db.collection.insert({'name': 'Randall'})
        doc = yield motor_db.collection.find_one()

See :ref:`the coroutine example <coroutine-example>`.

Requests
--------

PyMongo provides "requests" to ensure that a series of operations are performed
in order by the MongoDB server, even with unacknowledged writes (writes with
``w=0``). Motor does not support requests, so the only way to guarantee order
is by doing acknowledged writes. Register a callback for each operation and
perform the next operation in the callback::

    def inserted(result, error):
        if error:
            raise error

        db.users.find_one({'name': 'Ben'}, callback=found_one)

    def found_one(result, error):
        if error:
            raise error

        print result

    # Acknowledged insert:
    db.users.insert({'name': 'Ben', 'maintains': 'Tornado'}, callback=inserted)

This ensures ``find_one`` isn't run until ``insert`` has been acknowledged by
the server. Obviously, this code is improved by :mod:`tornado.gen`::

    @gen.coroutine
    def f():
        yield db.users.insert({'name': 'Ben', 'maintains': 'Tornado'})
        result = yield db.users.find_one({'name': 'Ben'})
        print result

Motor ignores the ``auto_start_request`` parameter to
`MotorClient` or `MotorReplicaSetClient`.

.. note:: Requests are deprecated in PyMongo 2.8 and will be removed in
   PyMongo 3.0.

Threading and forking
---------------------

Multithreading and forking are not supported; Motor is intended to be used in
a single-threaded Tornado application. See Tornado's documentation on
`running Tornado in production`_ to take advantage of multiple cores.

.. _`running Tornado in production`: http://www.tornadoweb.org/en/stable/guide/running.html

Minor differences
=================

Deprecated classes and options
------------------------------

PyMongo deprecated the ``slave_okay`` / ``slaveok`` option in favor of
:ref:`read preferences <secondary-reads>` in version 2.3. It deprecated
:class:`~pymongo.connection.Connection` and
:class:`~pymongo.replica_set_connection.ReplicaSetConnection` in favor of
:class:`~pymongo.mongo_client.MongoClient` and
:class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient` in version
2.4, as well as deprecating the ``safe`` option in favor of
:attr:`~motor.motor_tornado.MotorClient.write_concern`.
Motor supports none of PyMongo's deprecated options and classes at all, and
will raise :exc:`~pymongo.errors.ConfigurationError` if you use them.

MasterSlaveConnection
---------------------

PyMongo's :class:`~pymongo.master_slave_connection.MasterSlaveConnection`
offers a few conveniences when connected to a MongoDB `master-slave pair
<http://dochub.mongodb.org/core/masterslave>`_.
Master-slave replication has long been superseded by `replica sets
<http://dochub.mongodb.org/core/rs>`_, so Motor
has no equivalent to MasterSlaveConnection.

.. _gridfs-differences:

GridFS
------

- File-like

    PyMongo's :class:`~gridfs.grid_file.GridIn` and
    :class:`~gridfs.grid_file.GridOut` strive to act like Python's built-in
    file objects, so they can be passed to many functions that expect files.
    But the I/O methods of `MotorGridIn` and
    `MotorGridOut` are asynchronous, so they cannot obey the
    file API and aren't suitable in the same circumstances as files.

- Iteration

    It's convenient in PyMongo to iterate a :class:`~gridfs.grid_file.GridOut`::

        fs = gridfs.GridFS(db)
        grid_out = fs.get(file_id)
        for chunk in grid_out:
            print chunk

    `MotorGridOut` cannot support this API asynchronously.
    To read a ``MotorGridOut`` use the non-blocking
    `MotorGridOut.read` method. For convenience ``MotorGridOut``
    provides `MotorGridOut.stream_to_handler`.

    .. seealso:: :ref:`reading-from-gridfs` and :doc:`../api/web`

- Setting properties

    In PyMongo, you can set arbitrary attributes on
    a :class:`~gridfs.grid_file.GridIn` and they're stored as metadata on
    the server, even after the ``GridIn`` is closed::

        grid_in = fs.new_file()
        grid_in.close()
        grid_in.my_field = 'my_value'  # Sends update to server.

    Updating metadata on a `MotorGridIn` is asynchronous, so
    the API is different::

        @gen.coroutine
        def f():
            fs = motor.motor_tornado.MotorGridFS(db)
            yield fs.open()
            grid_in = yield fs.new_file()
            yield grid_in.close()

            # Sends update to server.
            yield grid_in.set('my_field', 'my_value')

    .. seealso:: :ref:`setting-attributes-on-a-motor-gridin`

- The "with" statement

    :class:`~gridfs.grid_file.GridIn` is a context manager--you can use it in a
    "with" statement and it is closed on exit::

        with fs.new_file() as grid_in:
            grid_in.write('data')

    But ``MotorGridIn``'s `MotorGridIn.close` method is
    asynchronous, so it must be called explicitly.

is_locked
---------

In PyMongo ``is_locked`` is a property of
:class:`~pymongo.mongo_client.MongoClient`. Since determining whether the
server has been fsyncLocked requires I/O, Motor has no such convenience method.
The equivalent in Motor is::

    result = yield client.admin.current_op()
    locked = bool(result.get('fsyncLock', None))

system_js
---------

PyMongo supports Javascript procedures stored in MongoDB with syntax like:

.. code-block:: python

    >>> db.system_js.my_func = 'function(x) { return x * x; }'
    >>> db.system_js.my_func(2)
    4.0

Motor does not.

Cursor slicing
--------------

In Pymongo, the following raises an ``IndexError`` if the collection has fewer
than 101 documents:

.. code-block:: python

    # Can raise IndexError.
    doc = db.collection.find()[100]

In Motor, however, no exception is raised. The query simply has no results:

.. code-block:: python

    @gen.coroutine
    def f():
        cursor = db.collection.find()[100]

        # Iterates zero or one times.
        while (yield cursor.fetch_next):
            doc = cursor.next_object()

The difference arises because the PyMongo :class:`~pymongo.cursor.Cursor`'s
slicing operator blocks until it has queried the MongoDB server, and determines
if a document exists at the desired offset; Motor simply returns a new
`MotorCursor` with a skip and limit applied.

Creating a collection
---------------------

There are two ways to create a capped collection using PyMongo:

.. code-block:: python

    # Typical:
    db.create_collection(
        'collection1',
        capped=True,
        size=1000)

    # Unusual:
    collection = Collection(
        db,
        'collection2',
        capped=True,
        size=1000)

Motor can't do I/O in a constructor, so the unusual style is prohibited and
only the typical style is allowed:

.. code-block:: python

    @gen.coroutine
    def f():
        yield db.create_collection(
            'collection1',
            capped=True,
            size=1000)
