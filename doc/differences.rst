.. currentmodule:: motor.motor_tornado

=====================================
Differences between Motor and PyMongo
=====================================

.. important:: This page describes using Motor with Tornado. Beginning in
  version 0.5 Motor can also integrate with asyncio instead of Tornado.

Major differences
=================

Connecting to MongoDB
---------------------

Motor provides a single client class, :class:`MotorClient`. Unlike PyMongo's
:class:`~pymongo.mongo_client.MongoClient`, Motor's client class does
not begin connecting in the background when it is instantiated. Instead it
connects on demand, when you first attempt an operation.

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

But Motor's :meth:`~MotorCollection.find_one` method is asynchronous:

.. code-block:: python

    db = MotorClient().test

    def got_user(user, error):
        if error:
            print 'error getting user!', error
        else:
            print user

    db.users.find_one({'name': 'Jesse'}, callback=got_user)

The callback must be passed as a keyword argument, not a positional argument.

To find multiple documents, Motor provides :meth:`~MotorCursor.to_list`:

.. code-block:: python

    def got_users(users, error):
        if error:
            print 'error getting users!', error
        else:
            for user in users:
                print user

    db.users.find().to_list(length=10, callback=got_users)

.. seealso:: :meth:`~MotorCursor.fetch_next`

If you pass no callback to an asynchronous method, it returns a Future for use
in a :func:`coroutine <tornado.gen.coroutine>`:

.. code-block:: python

    from tornado import gen

    @gen.coroutine
    def f():
        result = yield motor_db.collection.insert_one({'name': 'Randall'})
        doc = yield motor_db.collection.find_one()

See :ref:`the coroutine example <coroutine-example>`.

Threading and forking
---------------------

Multithreading and forking are not supported; Motor is intended to be used in
a single-threaded Tornado application. See Tornado's documentation on
`running Tornado in production`_ to take advantage of multiple cores.

.. _`running Tornado in production`: http://www.tornadoweb.org/en/stable/guide/running.html

Minor differences
=================

.. _gridfs-differences:

GridFS
------

- File-like

    PyMongo's :class:`~gridfs.grid_file.GridIn` and
    :class:`~gridfs.grid_file.GridOut` strive to act like Python's built-in
    file objects, so they can be passed to many functions that expect files.
    But the I/O methods of :class:`MotorGridIn` and
    :class:`MotorGridOut` are asynchronous, so they cannot obey the
    file API and aren't suitable in the same circumstances as files.

- Setting properties

    In PyMongo, you can set arbitrary attributes on
    a :class:`~gridfs.grid_file.GridIn` and they're stored as metadata on
    the server, even after the ``GridIn`` is closed::

        fs = gridfs.GridFSBucket(db)
        grid_in, file_id = fs.open_upload_stream('test_file')
        grid_in.close()
        grid_in.my_field = 'my_value'  # Sends update to server.

    Updating metadata on a :class:`MotorGridIn` is asynchronous, so
    the API is different::

        @gen.coroutine
        def f():
            fs = motor.motor_tornado.MotorGridFSBucket(db)
            grid_in, file_id = fs.open_upload_stream('test_file')
            yield grid_in.close()

            # Sends update to server.
            yield grid_in.set('my_field', 'my_value')

.. seealso:: :doc:`../api-tornado/gridfs`.

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
:class:`MotorCursor` with a skip and limit applied.

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
