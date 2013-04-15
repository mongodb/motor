=====================================
Differences between Motor and PyMongo
=====================================

Major differences
=================

Creating a connection
---------------------

PyMongo's :class:`~pymongo.mongo_client.MongoClient` and
:class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient` constructors
block until they have established a connection to MongoDB. A
:class:`~motor.MotorClient` or :class:`~motor.MotorReplicaSetClient`,
however, is created unconnected. One should call
:meth:`~motor.MotorClient.open_sync` at the beginning of a Tornado web
application, before accepting requests:

.. code-block:: python

    import motor
    client = motor.MotorClient().open_sync()

To make a connection asynchronously once the application is running, call
:meth:`~motor.MotorClient.open`:

.. code-block:: python

    def opened(client, error):
        if error:
            print 'Error connecting!', error
        else:
            # Use the client
            pass

    motor.MotorClient().open(opened)

Callbacks
---------

Motor supports nearly every method PyMongo does, but Motor methods that
do network I/O take a callback function. The callback must accept two
parameters:

.. code-block:: python

    def callback(result, error):
        pass

Motor's asynchronous methods return ``None`` immediately, and execute the
callback, with either a result or an error, when the operation has completed.

For example,
:meth:`~pymongo.collection.Collection.find_one` is used in PyMongo like:

.. code-block:: python

    db = MongoClient().test
    user = db.users.find_one({'name': 'Jesse'})
    print user

But Motor's :meth:`~motor.MotorCollection.find_one` method works asynchronously:

.. code-block:: python

    db = MotorClient().open_sync().test

    def got_user(user, error):
        if error:
            print 'error getting user!', error
        else:
            print user

    db.users.find_one({'name': 'Jesse'}, callback=got_user)

The callback must be passed as a keyword argument, not a positional argument.

To find multiple documents, Motor
provides :meth:`~motor.MotorCursor.to_list`:

.. code-block:: python

    def got_users(users, error):
        if error:
            print 'error getting users!', error
        else:
            for user in users:
                print user

    db.users.find().to_list(callback=got_users)

.. seealso:: MotorCursor's :meth:`~motor.MotorCursor.fetch_next`

.. _motor-acknowledged-writes:

Acknowledged Writes
-------------------

In Motor, writes are acknowledged by the server (they are "safe writes") if
passed a callback:

.. code-block:: python

    def on_inserted(result, error):
        if error:
            print 'error inserting!', error
        else:
            print 'added user'

    db.users.insert({'name': 'Bernie'}, callback=on_inserted) # Acknowledged

On success, the ``result`` parameter to the callback contains the
client-generated ``_id`` of the document for
:meth:`~motor.MotorCollection.insert` or :meth:`~motor.MotorCollection.save`,
and MongoDB's ``getLastError`` response for
:meth:`~motor.MotorCollection.update` or :meth:`~motor.MotorCollection.remove`.
On error, ``result`` is ``None`` and the ``error`` parameter is an Exception.

With no callback, Motor does unacknowledged writes.

One can pass ``w=0`` explicitly, along with a callback, to perform an
unacknowledged write:

.. code-block:: python

    db.users.insert({'name': 'Jesse'}, callback=inserted, w=0)

In this case the callback is executed as soon as the message has been written to
the socket connected to MongoDB, but no response is expected from the server.
Passing a callback and ``w=0`` can be useful to do fast writes without
opening an excessive number of connections.

Motor supports the same set of `write concerns`_ as PyMongo, but no matter what
write concern is configured, a write is acknowledged if passed a callback,
otherwise not.

.. _write concerns: http://api.mongodb.org/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient.write_concern

Result Values for Acknowledged and Unacknowledged Writes
''''''''''''''''''''''''''''''''''''''''''''''''''''''''

These are the values passed as the `result` parameter to your callback for
acknowledged and unacknowledged writes with Motor:

+-----------+-------------------------+--------------------------------+
| Operation | With Callback           | With Callback and `w=0`        |
+===========+=========================+================================+
| insert    | New \_id                | New \_id                       |
+-----------+-------------------------+--------------------------------+
| save      | \_id                    | \_id                           |
+-----------+-------------------------+--------------------------------+
| update    | ``{'ok': 1.0, 'n': 1}`` | ``None``                       |
+-----------+-------------------------+--------------------------------+
| remove    | ``{'ok': 1.0, 'n': 1}`` | ``None``                       |
+-----------+-------------------------+--------------------------------+

Unacknowledged Writes With gen.engine
'''''''''''''''''''''''''''''''''''''

When using Motor with `tornado.gen`_, each Motor operation is passed an implicit
callback and is therefore acknowledged ("safe"):

.. code-block:: python

    from tornado import gen

    @gen.engine
    def f():
        # Acknowledged
        yield motor.Op(motor_db.collection.insert, {'name': 'Randall'})

You can override this behavior and do unacknowledged writes by passing
``w=0``:

.. code-block:: python

    from tornado import gen

    @gen.engine
    def f():
        # Unacknowledged
        yield motor.Op(motor_db.collection.insert, {'name': 'Ross'}, w=0)

.. _tornado.gen: http://www.tornadoweb.org/documentation/gen.html

.. seealso:: :ref:`generator-interface`

max_concurrent and max_wait_time
--------------------------------

PyMongo allows the number of connections to MongoDB to grow to match the number
of threads performing concurrent operations. (PyMongo's ``max_pool_size``
merely caps the number of *idle* sockets kept open. [#max_pool_size]_)
:class:`~motor.MotorClient` and :class:`~motor.MotorReplicaSetClient` provide
an additional option, ``max_concurrent``, which caps the total number of
sockets per host, per client. The default is 100. Once the cap is reached,
operations yield to the IOLoop while waiting for a free socket. The optional
``max_wait_time`` allows operations to raise a :exc:`~motor.MotorPoolTimeout`
if they can't acquire a socket before the deadline.

Timeouts
--------

In PyMongo, you can set a network timeout which causes an
:exc:`~pymongo.errors.AutoReconnect` exception if an operation does not complete
in time::

    db = MongoClient(socketTimeoutMS=500).test
    try:
        user = db.users.find_one({'name': 'Jesse'})
        print user
    except AutoReconnect:
        print 'timed out'

:class:`~motor.MotorClient` and :class:`~motor.MotorReplicaSetClient`
support the same options. The exception isn't raised, instead it's passed to
the callback as the ``error`` parameter, and the ``result`` parameter will be
``None``. Code using `tornado.gen`_ ends up looking very similar to the
PyMongo code::

    @gen.engine
    def f():
        try:
            user = yield motor.Op(db.users.find_one, {'name': 'Jesse'})
            print user
        except AutoReconnect:
            print 'timed out'

As in PyMongo, the default ``connectTimeoutMS`` is 20 seconds, and the default
``socketTimeoutMS`` is no timeout.

Requests
--------

PyMongo provides "requests" to ensure that a series
of operations are performed in order by the MongoDB server, even with
unacknowledged writes. Motor does not support requests, so the only way to
guarantee order is by doing acknowledged writes. Register a callback
for each operation and perform the next operation in the callback::

    def inserted(result, error):
        if error:
            raise error

        db.users.find_one({'name': 'Ben'}, callback=found_one)

    def found_one(result, error):
        if error:
            raise error

        print result

    # Acknowledged insert:
    db.users.insert({'name': 'Ben', 'author': 'Tornado'}, callback=inserted)

This ensures ``find_one`` isn't run until ``insert`` has been acknowledged by
the server. Obviously, this code is improved by `tornado.gen`_::

    @gen.engine
    def f():
        yield motor.Op(db.users.insert, {'name': 'Ben', 'author': 'Tornado'})
        result = yield motor.Op(db.users.find_one, {'name': 'Ben'})
        print result

Motor ignores the ``auto_start_request`` parameter to
:class:`~motor.MotorClient` or :class:`~motor.MotorReplicaSetClient`.

.. _tornado.gen: http://www.tornadoweb.org/documentation/gen.html

Threading and forking
---------------------

Multithreading and forking are not supported; Motor is intended to be used in
a single-threaded Tornado application. See Tornado's documentation on
`running Tornado in production`_ to take advantage of multiple cores.

.. _`running Tornado in production`: http://www.tornadoweb.org/documentation/overview.html#running-tornado-in-production

Minor differences
=================

Deprecated classes and options
------------------------------

PyMongo deprecated the ``slave_okay`` / ``slaveok`` option in favor of
`read preferences`_ in version 2.3. It deprecated
:class:`~pymongo.connection.Connection` and
:class:`~pymongo.replica_set_connection.ReplicaSetConnection` in favor of
:class:`~pymongo.mongo_client.MongoClient` and
:class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient` in version
2.4, as well as deprecating the ``safe`` option in favor of `write concerns`_.
Motor supports none of PyMongo's deprecated options and classes at all, and
will raise :exc:`~pymongo.errors.ConfigurationError` if you use them.

.. _read preferences: http://api.mongodb.org/python/current/examples/high_availability.html#secondary-reads

MasterSlaveConnection
---------------------

PyMongo's :class:`~pymongo.master_slave_connection.MasterSlaveConnection`
offers a few conveniences when connected to a MongoDB `master-slave pair`_.
Master-slave replication has long been superseded by `replica sets`_, so Motor
has no equivalent to MasterSlaveConnection.

.. _master-slave pair: http://docs.mongodb.org/manual/administration/master-slave/

.. _replica sets: http://docs.mongodb.org/manual/core/replication/

.. _gridfs-differences:

GridFS
------

- File-like

    PyMongo's :class:`~gridfs.grid_file.GridIn` and
    :class:`~gridfs.grid_file.GridOut` strive to act like Python's built-in
    file objects, so they can be passed to many functions that expect files.
    But the I/O methods of :class:`~motor.MotorGridIn` and
    :class:`~motor.MotorGridOut` require callbacks, so they cannot obey the
    file API and aren't suitable in the same circumstances as files.

- Iteration

    It's convenient in PyMongo to iterate a :class:`~gridfs.grid_file.GridOut`::

        fs = gridfs.GridFS(db)
        grid_out = fs.get(file_id)
        for chunk in grid_out:
            print chunk

    :class:`~motor.MotorGridOut` cannot support this API asynchronously.
    To read a ``MotorGridOut`` use the non-blocking
    :meth:`~motor.MotorGridOut.read` method. For convenience ``MotorGridOut``
    provides :meth:`~motor.MotorGridOut.stream_to_handler`.

    .. seealso:: :ref:`reading-from-gridfs` and :doc:`../api/web`

- Setting properties

    In PyMongo, you can set arbitrary attributes on
    a :class:`~gridfs.grid_file.GridIn` and they're stored as metadata on
    the server, even after the ``GridIn`` is closed::

        grid_in = fs.new_file()
        grid_in.close()
        grid_in.my_field = 'my_value'

    Updating metadata on a :class:`~motor.MotorGridIn` requires a callback, so
    the API is different::

        @gen.engine
        def f():
            fs = motor.MotorGridFS(db)
            yield motor.Op(fs.open)
            grid_in = yield motor.Op(fs.new_file)
            yield motor.Op(grid_in.close)
            yield motor.Op(grid_in.set, 'my_field', 'my_value')

    .. seealso:: :ref:`setting-attributes-on-a-motor-gridin`

- The "with" statement

    :class:`~gridfs.grid_file.GridIn` is a context manager--you can use it in a
    "with" statement and it is closed on exit::

        with fs.new_file() as grid_in:
            grid_in.write('data')

    But ``MotorGridIn``'s :meth:`~motor.MotorGridIn.close` takes a callback, so
    it must be called explicitly.

is_locked
---------

:meth:`~motor.MotorClient.is_locked` in Motor is a method requiring a
callback, whereas in PyMongo it is a property of
:class:`~pymongo.mongo_client.MongoClient`.

system_js
---------

PyMongo supports Javascript procedures stored in MongoDB with syntax like:

.. code-block:: python

    >>> db.system_js.my_func = 'function(x) { return x * x; }'
    >>> db.system_js.my_func(2)
    4.0

Motor does not. One should use ``system.js`` as a regular collection with Motor:

.. code-block:: python

    def saved(result, error):
        if error:
            print 'error saving function!', error
        else:
            db.eval('my_func(2)', callback=evaluated)

    def evaluated(result, error):
        if error:
            print 'eval error!', error
        else:
            print 'eval result:', result # This will be 4.0

    db.system.js.save(
        {'_id': 'my_func', 'value': Code('function(x) { return x * x; }')},
        callback=saved)

.. seealso:: `Server-side code execution <http://docs.mongodb.org/manual/applications/server-side-javascript/>`_

Cursor slicing
--------------

In Pymongo, the following raises an ``IndexError`` if the collection has fewer
than 101 documents:

.. code-block:: python

    db.collection.find()[100]

In Motor, however, no exception is raised. The query simply has no results:

.. code-block:: python

    def callback(result, error):
        # 'result' is [ ] and 'error' is None
        print result, error

    db.collection.find()[100].to_list(callback)

The difference arises because the PyMongo :class:`~pymongo.cursor.Cursor`'s
slicing operator blocks until it has queried the MongoDB server, and determines
if a document exists at the desired offset; Motor simply returns a new
:class:`~motor.MotorCursor` with a skip and limit applied.

.. [#max_pool_size] See `PyMongo's max_pool_size
  <http://api.mongodb.org/python/current/api/pymongo/mongo_client.html#pymongo.mongo_client.MongoClient.max_pool_size>`_
