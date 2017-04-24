.. currentmodule:: motor.motor_tornado

Tutorial: Using Motor With Tornado
==================================

.. These setups are redundant because I can't figure out how to make doctest
  run a common setup *before* the setup for the two groups. A "testsetup:: *"
  is the obvious answer, but it's run *after* group-specific setup.

.. testsetup:: before-inserting-2000-docs

  import pymongo
  import motor
  import tornado.web
  from tornado.ioloop import IOLoop
  from tornado import gen
  db = motor.motor_tornado.MotorClient().test_database

.. testsetup:: after-inserting-2000-docs

  import pymongo
  import motor
  import tornado.web
  from tornado.ioloop import IOLoop
  from tornado import gen
  db = motor.motor_tornado.MotorClient().test_database
  sync_db = pymongo.MongoClient().test_database
  sync_db.test_collection.drop()
  sync_db.test_collection.insert_many(
      [{'i': i} for i in range(2000)])

.. testcleanup:: *

  import pymongo
  pymongo.MongoClient().test_database.test_collection.delete_many({})

A guide to using MongoDB and Tornado with Motor.

.. contents::

Tutorial Prerequisites
----------------------
You can learn about MongoDB with the `MongoDB Tutorial`_ before you learn Motor.

Install pip_ and then do::

  $ pip install tornado motor

Once done, the following should run in the Python shell without raising an
exception:

.. doctest::

  >>> import motor.motor_tornado

This tutorial also assumes that a MongoDB instance is running on the
default host and port. Assuming you have `downloaded and installed
<http://docs.mongodb.org/manual/installation/>`_ MongoDB, you
can start it like so:

.. code-block:: bash

  $ mongod

.. _pip: http://www.pip-installer.org/en/latest/installing.html

.. _MongoDB Tutorial: http://docs.mongodb.org/manual/tutorial/getting-started/

Object Hierarchy
----------------
Motor, like PyMongo, represents data with a 4-level object hierarchy:

* :class:`MotorClient` represents a mongod process, or a cluster of them. You
  explicitly create one of these client objects, connect it to a running mongod
  or mongods, and use it for the lifetime of your application.
* :class:`MotorDatabase`: Each mongod has a set of databases (distinct
  sets of data files on disk). You can get a reference to a database from a
  client.
* :class:`MotorCollection`: A database has a set of collections, which
  contain documents; you get a reference to a collection from a database.
* :class:`MotorCursor`: Executing :meth:`~MotorCollection.find` on
  a :class:`MotorCollection` gets a :class:`MotorCursor`, which
  represents the set of documents matching a query.

Creating a Client
-----------------
You typically create a single instance of :class:`MotorClient` at the time your
application starts up.

.. doctest:: before-inserting-2000-docs

  >>> client = motor.motor_tornado.MotorClient()

This connects to a ``mongod`` listening on the default host and port. You can
specify the host and port like:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.motor_tornado.MotorClient('localhost', 27017)

Motor also supports `connection URIs`_:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.motor_tornado.MotorClient('mongodb://localhost:27017')

Connect to a replica set like:

  >>> client = motor.motor_tornado.MotorClient('mongodb://host1,host2/?replicaSet=my-replicaset-name')

.. _connection URIs: http://docs.mongodb.org/manual/reference/connection-string/

Getting a Database
------------------
A single instance of MongoDB can support multiple independent
`databases <http://docs.mongodb.org/manual/reference/glossary/#term-database>`_.
From an open client, you can get a reference to a particular database with
dot-notation or bracket-notation:

.. doctest:: before-inserting-2000-docs

  >>> db = client.test_database
  >>> db = client['test_database']

Creating a reference to a database does no I/O and does not accept a callback
or return a Future.

Tornado Application Startup Sequence
------------------------------------
Now that we can create a client and get a database, we're ready to start
a Tornado application that uses Motor::

    db = motor.motor_tornado.MotorClient().test_database

    application = tornado.web.Application([
        (r'/', MainHandler)
    ], db=db)

    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

There are two things to note in this code. First, the ``MotorClient``
constructor doesn't actually connect to the server; the client will
initiate a connection when you attempt the first operation.
Second, passing the database as the ``db`` keyword argument to ``Application``
makes it available to request handlers::

    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            db = self.settings['db']

It is a common mistake to create a new client object for every
request; **this comes at a dire performance cost**. Create the client
when your application starts and reuse that one client for the lifetime
of the process, as shown in these examples.

The Tornado :class:`~tornado.httpserver.HTTPServer` class's :meth:`start`
method is a simple way to fork multiple web servers and use all of your
machine's CPUs. However, you must create your ``MotorClient`` after forking::

    # Create the application before creating a MotorClient.
    application = tornado.web.Application([
        (r'/', MainHandler)
    ])

    server = tornado.httpserver.HTTPServer(application)
    server.bind(8888)

    # Forks one process per CPU.
    server.start(0)

    # Now, in each child process, create a MotorClient.
    application.settings['db'] = MotorClient().test_database
    IOLoop.current().start()

For production-ready, multiple-CPU deployments of Tornado there are better
methods than ``HTTPServer.start()``. See Tornado's guide to
:doc:`tornado:guide/running`.

Getting a Collection
--------------------
A `collection <http://docs.mongodb.org/manual/reference/glossary/#term-collection>`_
is a group of documents stored in MongoDB, and can be thought of as roughly
the equivalent of a table in a relational database. Getting a
collection in Motor works the same as getting a database:

.. doctest:: before-inserting-2000-docs

  >>> collection = db.test_collection
  >>> collection = db['test_collection']

Just like getting a reference to a database, getting a reference to a
collection does no I/O and doesn't accept a callback or return a Future.

Inserting a Document
--------------------
As in PyMongo, Motor represents MongoDB documents with Python dictionaries. To
store a document in MongoDB, call :meth:`~MotorCollection.insert_one` with a
document and a callback:

.. doctest:: before-inserting-2000-docs

  >>> from tornado.ioloop import IOLoop
  >>> def my_callback(result, error):
  ...     print('result %s' % repr(result.inserted_id))
  ...     IOLoop.current().stop()
  ...
  >>> document = {'key': 'value'}
  >>> db.test_collection.insert_one(document, callback=my_callback)
  >>> IOLoop.current().start()
  result ObjectId('...')

There are several differences to note between Motor and PyMongo. One is that,
unlike PyMongo's :meth:`~pymongo.collection.Collection.insert_one`, Motor's has no
return value. Another is that ``insert_one`` accepts an optional callback function.
The function must take two arguments and it must be passed to ``insert_one`` as a
keyword argument, like::

  db.test_collection.insert_one(document, callback=some_function)

.. warning:: Passing the callback function using the ``callback=`` syntax is
  required. (This requirement is a side-effect of the technique Motor uses to
  wrap PyMongo.) If you pass the callback as a positional argument instead,
  you may see an exception like ``TypeError: method takes exactly 1 argument (2
  given)``, or ``TypeError: callable is required``, or some silent misbehavior.

:meth:`insert_one` is *asynchronous*. This means it returns immediately, and
the actual work of inserting the document into the collection is performed in
the background. When it completes, the callback is executed. If the insert
succeeded, the ``result`` parameter is a
:class:`~pymongo.results.InsertOneResult` with the new document's unique id and
the ``error`` parameter is ``None``. If there was an error, ``result`` is
``None`` and ``error`` is an ``Exception`` object. For example, we can trigger
a duplicate-key error by trying to insert two documents with the same unique
id:

.. doctest:: before-inserting-2000-docs

  >>> loop = IOLoop.current()
  >>> def my_callback(result, error):
  ...     print('result %s error %s' % (repr(result), repr(error)))
  ...     IOLoop.current().stop()
  ...
  >>> def insert_two_documents():
  ...     db.test_collection.insert_one({'_id': 1}, callback=my_callback)
  ...
  >>> IOLoop.current().add_callback(insert_two_documents)
  >>> IOLoop.current().start()
  result <pymongo.results.InsertOneResult ...> error None
  >>> IOLoop.current().add_callback(insert_two_documents)
  >>> IOLoop.current().start()
  result None error DuplicateKeyError(...)

The first insert results in ``my_callback`` being called with result 1 and
error ``None``. The second insert triggers ``my_callback`` with result None and
a :class:`~pymongo.errors.DuplicateKeyError`.

A typical beginner's mistake with Motor is to insert documents in a loop,
not waiting for each insert to complete before beginning the next::

  >>> for i in range(2000):
  ...     db.test_collection.insert_one({'i': i})

.. Note that the above is NOT a doctest!!

In PyMongo this would insert each document in turn using a single socket, but
Motor attempts to run all the :meth:`insert_one` operations at once. This requires
up to ``max_pool_size`` open sockets connected to MongoDB,
which taxes the client and server. To ensure instead that all inserts use a
single connection, wait for acknowledgment of each. This is a bit complex using
callbacks:

.. doctest:: before-inserting-2000-docs

  >>> i = 0
  >>> def do_insert(result, error):
  ...     global i
  ...     if error:
  ...         raise error
  ...     i += 1
  ...     if i < 2000:
  ...         db.test_collection.insert_one({'i': i}, callback=do_insert)
  ...     else:
  ...         IOLoop.current().stop()
  ...
  >>> # Start
  >>> db.test_collection.insert_one({'i': i}, callback=do_insert)
  >>> IOLoop.current().start()

You can simplify this code with ``gen.coroutine``.

Using Motor with `gen.coroutine`
--------------------------------
The :mod:`tornado.gen` module lets you use generators to simplify asynchronous
code. There are two parts to coding with generators:
:func:`coroutine <tornado.gen.coroutine>` and
:class:`~tornado.concurrent.Future`.

First, decorate your generator function with ``@gen.coroutine``:

  >>> @gen.coroutine
  ... def do_insert():
  ...     pass

If you pass no callback to one of Motor's asynchronous methods, it returns a
``Future``. Yield the ``Future`` instance to wait for an operation to complete
and obtain its result:

.. doctest:: before-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_insert():
  ...     for i in range(2000):
  ...         future = db.test_collection.insert_one({'i': i})
  ...         result = yield future
  ...
  >>> IOLoop.current().run_sync(do_insert)

In the code above, ``result`` is the ``_id`` of each inserted document.

.. seealso:: :doc:`examples/bulk`.

.. seealso:: :ref:`Detailed example of Motor and gen.coroutine <coroutine-example>`

.. mongodoc:: insert

.. doctest:: before-inserting-2000-docs
  :hide:

  >>> # Clean up from previous insert
  >>> pymongo.MongoClient().test_database.test_collection.delete_many({})
  <pymongo.results.DeleteResult ...>

Using native coroutines
-----------------------

Starting in Python 3.5, you can define a `native coroutine`_ with `async def`
instead of the `gen.coroutine` decorator. Within a native coroutine, wait
for an async operation with `await` instead of `yield`:

.. doctest:: before-inserting-2000-docs

  >>> async def do_insert():
  ...     for i in range(2000):
  ...         result = await db.test_collection.insert_one({'i': i})
  ...
  >>> IOLoop.current().run_sync(do_insert)

Within a native coroutine, the syntax to use Motor with Tornado or asyncio
is often identical.

.. _native coroutine: https://www.python.org/dev/peps/pep-0492/

Getting a Single Document With :meth:`~MotorCollection.find_one`
----------------------------------------------------------------
Use :meth:`~MotorCollection.find_one` to get the first document that
matches a query. For example, to get a document where the value for key "i" is
less than 1:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_find_one():
  ...     document = yield db.test_collection.find_one({'i': {'$lt': 1}})
  ...     pprint.pprint(document)
  ...
  >>> IOLoop.current().run_sync(do_find_one)
  {'_id': ObjectId('...'), 'i': 0}

The result is a dictionary matching the one that we inserted previously.

The returned document contains an ``"_id"``, which was
automatically added on insert.

(We use ``pprint`` here instead of ``print`` to ensure the document's key names
are sorted the same in your output as ours.)

.. mongodoc:: find

Querying for More Than One Document
-----------------------------------
Use :meth:`~MotorCollection.find` to query for a set of documents.
:meth:`~MotorCollection.find` does no I/O and does not take a callback,
it merely creates a :class:`MotorCursor` instance. The query is actually
executed on the server when you call :meth:`~MotorCursor.to_list` or
:meth:`~MotorCursor.each`, or yield :attr:`~motor.motor_tornado.MotorCursor.fetch_next`.

To find all documents with "i" less than 5:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}}).sort('i')
  ...     for document in (yield cursor.to_list(length=100)):
  ...         pprint.pprint(document)
  ...
  >>> IOLoop.current().run_sync(do_find)
  {'_id': ObjectId('...'), 'i': 0}
  {'_id': ObjectId('...'), 'i': 1}
  {'_id': ObjectId('...'), 'i': 2}
  {'_id': ObjectId('...'), 'i': 3}
  {'_id': ObjectId('...'), 'i': 4}

A ``length`` argument is required when you call to_list to prevent Motor from
buffering an unlimited number of documents.

To get one document at a time with :attr:`~motor.motor_tornado.MotorCursor.fetch_next`
and :meth:`~MotorCursor.next_object`:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}})
  ...     while (yield cursor.fetch_next):
  ...         document = cursor.next_object()
  ...         pprint.pprint(document)
  ...
  >>> IOLoop.current().run_sync(do_find)
  {'_id': ObjectId('...'), 'i': 0}
  {'_id': ObjectId('...'), 'i': 1}
  {'_id': ObjectId('...'), 'i': 2}
  {'_id': ObjectId('...'), 'i': 3}
  {'_id': ObjectId('...'), 'i': 4}

You can apply a sort, limit, or skip to a query before you begin iterating:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_find():
  ...     c = db.test_collection
  ...     cursor = c.find({'i': {'$lt': 5}})
  ...     # Modify the query before iterating
  ...     cursor.sort('i', -1).limit(2).skip(2)
  ...     while (yield cursor.fetch_next):
  ...         document = cursor.next_object()
  ...         pprint.pprint(document)
  ...
  >>> IOLoop.current().run_sync(do_find)
  {'_id': ObjectId('...'), 'i': 2}
  {'_id': ObjectId('...'), 'i': 1}

``fetch_next`` does not actually retrieve each document from the server
individually; it gets documents efficiently in `large batches`_.

.. _`large batches`: https://docs.mongodb.com/manual/tutorial/iterate-a-cursor/#cursor-batches

`async for`
-----------

In a native coroutine defined with `async def`, replace the while-loop with
`async for`:

.. doctest:: after-inserting-2000-docs

  >>> async def do_find():
  ...     c = db.test_collection
  ...     async for document in c.find({'i': {'$lt': 2}}):
  ...         pprint.pprint(document)
  ...
  >>> IOLoop.current().run_sync(do_find)
  {'_id': ObjectId('...'), 'i': 0}
  {'_id': ObjectId('...'), 'i': 1}

This version of the code is dramatically faster.

Counting Documents
------------------
Use :meth:`~MotorCursor.count` to determine the number of documents in
a collection, or the number of documents that match a query:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_count():
  ...     n = yield db.test_collection.find().count()
  ...     print('%s documents in collection' % n)
  ...     n = yield db.test_collection.find({'i': {'$gt': 1000}}).count()
  ...     print('%s documents where i > 1000' % n)
  ...
  >>> IOLoop.current().run_sync(do_count)
  2000 documents in collection
  999 documents where i > 1000

:meth:`~MotorCursor.count` uses the *count command* internally; we'll
cover commands_ below.

.. seealso:: `Count command <http://docs.mongodb.org/manual/reference/command/count/>`_

Updating Documents
------------------

:meth:`~MotorCollection.replace_one` changes a document. It requires two
parameters: a *query* that specifies which document to replace, and a
replacement document. The query follows the same syntax as for :meth:`find` or
:meth:`find_one`. To replace a document:

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_replace():
  ...     coll = db.test_collection
  ...     old_document = yield coll.find_one({'i': 50})
  ...     print('found document: %s' % pprint.pformat(old_document))
  ...     _id = old_document['_id']
  ...     result = yield coll.replace_one({'_id': _id}, {'key': 'value'})
  ...     print('replaced %s document' % result.modified_count)
  ...     new_document = yield coll.find_one({'_id': _id})
  ...     print('document is now %s' % pprint.pformat(new_document))
  ...
  >>> IOLoop.current().run_sync(do_replace)
  found document: {'_id': ObjectId('...'), 'i': 50}
  replaced 1 document
  document is now {'_id': ObjectId('...'), 'key': 'value'}

You can see that :meth:`replace_one` replaced everything in the old document
except its ``_id`` with the new document.

Use :meth:`~MotorCollection.update_one` with MongoDB's modifier operators to
update part of a document and leave the
rest intact. We'll find the document whose "i" is 51 and use the ``$set``
operator to set "key" to "value":

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_update():
  ...     coll = db.test_collection
  ...     result = yield coll.update_one({'i': 51}, {'$set': {'key': 'value'}})
  ...     print('updated %s document' % result.modified_count)
  ...     new_document = yield coll.find_one({'i': 51})
  ...     print('document is now %s' % pprint.pformat(new_document))
  ...
  >>> IOLoop.current().run_sync(do_update)
  updated 1 document
  document is now {'_id': ObjectId('...'), 'i': 51, 'key': 'value'}

"key" is set to "value" and "i" is still 51.

:meth:`update_one` only affects the first document it finds, you can
update all of them with :meth:`update_many`::

    yield coll.update_many({'i': {'$gt': 100}},
                           {'$set': {'key': 'value'}})

.. mongodoc:: update

Removing Documents
------------------

:meth:`~MotorCollection.delete_many` takes a query with the same syntax as
:meth:`~MotorCollection.find`.
:meth:`delete_many` immediately removes all matching documents.

.. doctest:: after-inserting-2000-docs

  >>> @gen.coroutine
  ... def do_delete_many():
  ...     coll = db.test_collection
  ...     n = yield coll.count()
  ...     print('%s documents before calling delete_many()' % n)
  ...     result = yield db.test_collection.delete_many({'i': {'$gte': 1000}})
  ...     print('%s documents after' % (yield coll.count()))
  ...
  >>> IOLoop.current().run_sync(do_delete_many)
  2000 documents before calling delete_many()
  1000 documents after

.. mongodoc:: remove

Commands
--------
Besides the "CRUD" operations--insert, update, delete, and find--all other
operations on MongoDB are commands. Run them using
the :meth:`~MotorDatabase.command` method on :class:`MotorDatabase`:

.. doctest:: after-inserting-2000-docs

  >>> from bson import SON
  >>> @gen.coroutine
  ... def use_count_command():
  ...     response = yield db.command(SON([("count", "test_collection")]))
  ...     print('response: %s' % pprint.pformat(response))
  ...
  >>> IOLoop.current().run_sync(use_count_command)
  response: {'n': 1000, 'ok': 1.0...}

Since the order of command parameters matters, don't use a Python dict to pass
the command's parameters. Instead, make a habit of using :class:`bson.SON`,
from the ``bson`` module included with PyMongo::

    yield db.command(SON([("distinct", "test_collection"), ("key", "my_key")]))

Many commands have special helper methods, such as
:meth:`~MotorDatabase.create_collection` or
:meth:`~MotorCollection.aggregate`, but these are just conveniences atop
the basic :meth:`command` method.

.. mongodoc:: commands

Further Reading
---------------
The handful of classes and methods introduced here are sufficient for daily
tasks. The API documentation for :class:`MotorClient`, :class:`MotorDatabase`,
:class:`MotorCollection`, and :class:`MotorCursor` provides a
reference to Motor's complete feature set.

Learning to use the MongoDB driver is just the beginning, of course. For
in-depth instruction in MongoDB itself, see `The MongoDB Manual`_.

.. _The MongoDB Manual: http://docs.mongodb.org/manual/
