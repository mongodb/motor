.. _motor-tutorial:

Motor Tutorial
==============

.. These setups are redundant because I can't figure out how to make doctest
  run a common setup *before* the setup for the two groups. A "testsetup:: *"
  is the obvious answer, but it's run *after* group-specific setup.

.. testsetup:: before-inserting-2000-docs

  import pymongo
  import motor
  import tornado.web
  from tornado.ioloop import IOLoop
  from tornado import gen
  db = motor.MotorClient().open_sync().test_database

.. testsetup:: after-inserting-2000-docs

  import pymongo
  import motor
  import tornado.web
  from tornado.ioloop import IOLoop
  from tornado import gen
  db = motor.MotorClient().open_sync().test_database
  pymongo.MongoClient().test_database.test_collection.insert(
      [{'i': i} for i in range(2000)])

.. testcleanup:: *

  import pymongo
  pymongo.MongoClient().test_database.test_collection.remove()

A guide to using **MongoDB** and **Tornado** with **Motor**, the
non-blocking driver.

Tutorial Prerequisites
----------------------
You can learn about MongoDB with the `MongoDB Tutorial`_ before you learn Motor.

Install pip_ and then do:

  $ pip install motor

Once done, the following should run in the Python shell without raising an
exception:

.. doctest::

  >>> import motor

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

* :class:`~motor.MotorClient` / :class:`~motor.MotorReplicaSetClient`:
  represents a mongod process, or a cluster of them. You explicitly create one
  of these client objects, connect it to a running mongod or mongods, and
  use it for the lifetime of your application.
* :class:`~motor.MotorDatabase`: Each mongod has a set of databases (distinct
  sets of data files on disk). You can get a reference to a database from a
  client.
* :class:`~motor.MotorCollection`: A database has a set of collections, which
  contain documents; you get a reference to a collection from a database.
* :class:`~motor.MotorCursor`: Executing :meth:`~motor.MotorCollection.find` on
  a :class:`~motor.MotorCollection` gets a :class:`~motor.MotorCursor`, which
  represents the set of documents matching a query.

Creating a Client
-----------------
You typically create a single instance of either :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient` at the time your application starts
up. (See `high availability and PyMongo`_ for an introduction to
MongoDB replica sets and how PyMongo connects to them.)

You must call :meth:`~motor.MotorClient.open_sync` on this client object
before any other operations on it:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.MotorClient().open_sync()

This connects to a ``mongod`` listening on the default host and port. You can
specify the host and port like:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.MotorClient('localhost', 27017).open_sync()

Motor also supports `connection URIs`_::

  >>> client = motor.MotorClient('mongodb://localhost:27017').open_sync()

.. _high availability and PyMongo: http://api.mongodb.org/python/current/examples/high_availability.html

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

Creating a reference to a database does no I/O and does not require a callback.

Tornado Application Startup Sequence
------------------------------------
Now that we can create a client and get a database, we're ready to start
a Tornado application that uses Motor.

:meth:`~motor.MotorClient.open_sync` is a blocking operation so it should
be called before listening for HTTP requests. Here's an example startup
sequence for a Tornado web application::

    db = motor.MotorClient().open_sync().test_database

    application = tornado.web.Application([
        (r'/', MainHandler)
    ], db=db)

    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

Passing the database as the ``db`` keyword argument to ``Application`` makes it
available to request handlers::

    class MainHandler(tornado.web.RequestHandler):
        def get(self):
            db = self.settings['db']

If you want to use the Tornado HTTP server's `start() method`_ to fork
multiple subprocesses, you must create the client object **after** calling
``start()``, since a client created before forking isn't valid after::

    application = tornado.web.Application([
        (r'/', MainHandler)
    ])

    server = tornado.httpserver.HTTPServer(application)
    server.bind(8888)

    # start(0) starts a subprocess for each CPU core
    server.start(0)

    db = motor.MotorClient().open_sync().test_database

    # Delayed initialization of settings
    application.settings['db'] = db
    tornado.ioloop.IOLoop.instance().start()

.. warning:: It is a common mistake to create a new client object for every
  request; this comes at a dire performance cost. Create the client
  when your application starts and reuse that one client for the lifetime
  of the process, as shown in these examples.

.. _start() method: http://www.tornadoweb.org/documentation/netutil.html#tornado.netutil.TCPServer.start

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
collection does no I/O and doesn't require a callback.

Inserting a Document
--------------------
As in PyMongo, Motor represents MongoDB documents with Python dictionaries. To
store a document in MongoDB, call :meth:`~motor.MotorCollection.insert` with a
document and a callback:

.. doctest:: before-inserting-2000-docs

  >>> from tornado.ioloop import IOLoop
  >>> def my_callback(result, error):
  ...     print 'result', repr(result)
  ...     IOLoop.instance().stop()
  ...
  >>> document = {'key': 'value'}
  >>> db.test_collection.insert(document, callback=my_callback)
  >>> IOLoop.instance().start()
  result ObjectId('...')

There are several differences to note between Motor and PyMongo. One is that,
unlike PyMongo's :meth:`~pymongo.collection.Collection.insert`, Motor's has no
return value. Another is that ``insert`` accepts an optional callback function.
The function must take two arguments and it must be passed to ``insert`` as a
keyword argument, like::

  db.test_collection.insert(document, callback=some_function)

.. warning:: Passing the callback function using the ``callback=`` syntax is
  required. (This requirement is a side-effect of the technique Motor uses to
  wrap PyMongo.) If you pass the callback as a positional argument instead,
  you may see an exception like ``TypeError: method takes exactly 1 argument (2
  given)``, or ``TypeError: callable is required``, or some silent misbehavior.

:meth:`insert` is *asynchronous*. This means it returns immediately, and the
actual work of inserting the document into the collection is performed in the
background. When it completes, the callback is executed. If the
insert succeeded, the ``result`` parameter is the new document's unique id
and the ``error`` parameter is ``None``. If there was an error, ``result`` is
``None`` and ``error`` is an ``Exception`` object. For example, we can
trigger a duplicate-key error by trying to insert two documents with the same
unique id:

.. doctest:: before-inserting-2000-docs

  >>> ncalls = 0
  >>> def my_callback(result, error):
  ...     global ncalls
  ...     print 'result', repr(result), 'error', repr(error)
  ...     ncalls += 1
  ...     if ncalls == 2:
  ...         IOLoop.instance().stop()
  ...
  >>> document = {'_id': 1}
  >>> db.test_collection.insert(document, callback=my_callback)
  >>> db.test_collection.insert(document, callback=my_callback)
  >>> IOLoop.instance().start()
  result 1 error None
  result None error DuplicateKeyError(u'E11000 duplicate key error index: test_database.test_collection.$_id_  dup key: { : 1 }',)

The first insert results in ``my_callback`` being called with result 1 and
error ``None``. The second insert triggers ``my_callback`` with result None and
a :class:`~pymongo.errors.DuplicateKeyError`.

.. seealso:: :ref:`Acknowledged writes in Motor <motor-acknowledged-writes>`

A typical beginner's mistake with Motor is to insert documents in a loop,
not waiting for each insert to complete before beginning the next::

  >>> for i in range(2000):
  ...     db.test_collection.insert({'i': i})

.. Note that the above is NOT a doctest!!

In PyMongo this would insert each document in turn using a single socket, but
Motor attempts to run all the :meth:`insert` operations at once. This requires
up to ``max_concurrent`` [#max_concurrent]_ open sockets connected to MongoDB,
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
  ...         db.test_collection.insert({'i': i}, callback=do_insert)
  ...     else:
  ...         IOLoop.instance().stop()
  ...
  >>> # Start
  >>> db.test_collection.insert({'i': i}, callback=do_insert)
  >>> IOLoop.instance().start()

You can simplify this code with ``gen.engine``.

Using Motor with `gen.engine`
-----------------------------
The `tornado.gen module`_
lets you use generators to simplify asynchronous code, combining operations and
their callbacks in a single function. You must decorate the function with
``@gen.engine`` and yield ``gen.Task`` instances to wait for operations to
complete:

.. doctest:: before-inserting-2000-docs

  >>> @gen.engine
  ... def do_insert():
  ...     for i in range(2000):
  ...         arguments = yield gen.Task(db.test_collection.insert, {'i': i})
  ...         result, error = arguments.args
  ...         if error:
  ...             raise error
  ...     IOLoop.instance().stop()
  ...
  >>> # Start
  >>> do_insert()
  >>> IOLoop.instance().start()

Here ``arguments`` is an instance of `tornado.gen.Arguments`_
containing the arguments :meth:`insert` passed to its callback function.
Motor provides :class:`~motor.Op` to further simplify asynchronous operations
with ``gen.engine``:

.. doctest:: before-inserting-2000-docs

  >>> @gen.engine
  ... def do_insert():
  ...     for i in range(2000):
  ...         result = yield motor.Op(db.test_collection.insert, {'i': i})
  ...     IOLoop.instance().stop()
  ...
  >>> do_insert()
  >>> IOLoop.instance().start()

:class:`~motor.Op` receives the ``result`` and ``error`` parameters and either
raises the error or returns the result. In the code above, ``result`` is the
``_id`` of each inserted document.

.. seealso:: `Bulk inserts in PyMongo <http://api.mongodb.org/python/current/tutorial.html?highlight=bulk%20inserts#bulk-inserts>`_

.. seealso:: :ref:`Detailed example of Motor and gen.engine <generator-interface-example>`

.. _tornado.gen module: http://www.tornadoweb.org/documentation/gen.html

.. _tornado.gen.Arguments: http://www.tornadoweb.org/documentation/gen.html#tornado.gen.Arguments

.. mongodoc:: insert

Getting a Single Document With :meth:`~motor.MotorCollection.find_one`
----------------------------------------------------------------------
Use :meth:`~motor.MotorCollection.find_one` to get the first document that
matches a query. For example, to get a document where the value for key "i" is
less than 2:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_find_one():
  ...     document = yield motor.Op(
  ...         db.test_collection.find_one, {'i': {'$lt': 2}})
  ...     print document
  ...     IOLoop.instance().stop()
  ...
  >>> do_find_one()
  >>> IOLoop.instance().start()
  {u'i': 0, u'_id': ObjectId('...')}

The result is a dictionary matching the one that we inserted previously.

.. note:: The returned document contains an ``"_id"``, which was
   automatically added on insert.

.. mongodoc:: find

Querying for More Than One Document
-----------------------------------
Use :meth:`~motor.MotorCollection.find` to query for a set of documents.
:meth:`~motor.MotorCollection.find` does no I/O and does not take a callback,
it merely creates a :class:`~motor.MotorCursor` instance. The query is actually
executed on the server when you call :meth:`~motor.MotorCursor.to_list` or
:meth:`~motor.MotorCursor.each`, or yield :attr:`~motor.MotorCursor.fetch_next`.

To find all documents with "i" less than 5:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}})
  ...     for document in (yield motor.Op(cursor.to_list)):
  ...         print document
  ...     IOLoop.instance().stop()
  ...
  >>> do_find()
  >>> IOLoop.instance().start()
  {u'i': 0, u'_id': ObjectId('...')}
  {u'i': 1, u'_id': ObjectId('...')}
  {u'i': 2, u'_id': ObjectId('...')}
  {u'i': 3, u'_id': ObjectId('...')}
  {u'i': 4, u'_id': ObjectId('...')}

To iterate over a large result set without holding all the documents in memory
at once, get one document at a time with :attr:`~motor.MotorCursor.fetch_next`
and :meth:`~motor.MotorCursor.next_object`:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}})
  ...     while (yield cursor.fetch_next):
  ...         document = cursor.next_object()
  ...         print document
  ...     IOLoop.instance().stop()
  ...
  >>> do_find()
  >>> IOLoop.instance().start()
  {u'i': 0, u'_id': ObjectId('...')}
  {u'i': 1, u'_id': ObjectId('...')}
  {u'i': 2, u'_id': ObjectId('...')}
  {u'i': 3, u'_id': ObjectId('...')}
  {u'i': 4, u'_id': ObjectId('...')}

.. note:: ``fetch_next`` doesn't need to be used with ``yield motor.Op``; it's
  already a yieldable object so you simply ``yield cursor.fetch_next``.

You can apply a sort, limit, or skip to a query before you begin iterating:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}})
  ...     # Modify the query before iterating
  ...     cursor.sort([('i', pymongo.DESCENDING)]).limit(2).skip(2)
  ...     while (yield cursor.fetch_next):
  ...         document = cursor.next_object()
  ...         print document
  ...     IOLoop.instance().stop()
  ...
  >>> do_find()
  >>> IOLoop.instance().start()
  {u'i': 2, u'_id': ObjectId('...')}
  {u'i': 1, u'_id': ObjectId('...')}

Counting Documents
------------------
Use :meth:`~motor.MotorCursor.count` to determine the number of documents in
a collection, or the number of documents that match a query:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_count():
  ...     n = yield motor.Op(db.test_collection.find().count)
  ...     print n, 'documents in collection'
  ...     n = yield motor.Op(
  ...         db.test_collection.find({'i': {'$gt': 1000}}).count)
  ...     print n, 'documents where i > 1000'
  ...     IOLoop.instance().stop()
  ...
  >>> do_count()
  >>> IOLoop.instance().start()
  2000 documents in collection
  999 documents where i > 1000

:meth:`~motor.MotorCursor.count` uses the *count command* internally; we'll
cover commands_ below.

.. seealso:: `Count command <http://docs.mongodb.org/manual/reference/command/count/>`_

Updating Documents
------------------
:meth:`~motor.MotorCollection.update` changes documents. It requires two
parameters: a *query* that specifies which documents to update, and an update
document. The query follows the same syntax as for :meth:`find` or
:meth:`find_one`. The update document has two modes: it can replace the whole
document, or it can update some fields of a document. To replace a document:

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_replace():
  ...     coll = db.test_collection
  ...     old_document = yield motor.Op(coll.find_one, {'i': 50})
  ...     print 'found document:', old_document
  ...     _id = old_document['_id']
  ...     result = yield motor.Op(coll.update, {'_id': _id}, {'key': 'value'})
  ...     print 'replaced', result['n'], 'document'
  ...     new_document = yield motor.Op(coll.find_one, {'_id': _id})
  ...     print 'document is now', new_document
  ...     IOLoop.instance().stop()
  ...
  >>> do_replace()
  >>> IOLoop.instance().start()
  found document: {u'i': 50, u'_id': ObjectId('...')}
  replaced 1 document
  document is now {u'_id': ObjectId('...'), u'key': u'value'}

You can see that :meth:`update` replaced everything in the old document except
its ``_id`` with the new document.

Use MongoDB's modifier operators to update part of a document and leave the
rest intact. We'll find the document whose "i" is 51 and use the ``$set``
operator to set "key" to "value":

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_update():
  ...     coll = db.test_collection
  ...     result = yield motor.Op(coll.update,
  ...         {'i': 51}, {'$set': {'key': 'value'}})
  ...     print 'updated', result['n'], 'document'
  ...     new_document = yield motor.Op(coll.find_one, {'i': 51})
  ...     print 'document is now', new_document
  ...     IOLoop.instance().stop()
  ...
  >>> do_update()
  >>> IOLoop.instance().start()
  updated 1 document
  document is now {u'i': 51, u'_id': ObjectId('...'), u'key': u'value'}

"key" is set to "value" and "i" is still 51.

By default :meth:`update` only affects the first document it finds, you can
update all of them with the ``multi`` flag::

    yield motor.Op(coll.update,
        {'i': {'$gt': 100}}, {'$set': {'key': 'value'}}, multi=True)

.. mongodoc:: update

Saving Documents
----------------

:meth:`~motor.MotorCollection.save` is a convenience method provided to insert
a new document or update an existing one. If the dict passed to :meth:`save`
has an ``"_id"`` key then Motor performs an :meth:`update` (upsert) operation
and any existing document with that ``"_id"`` is overwritten. Otherwise Motor
performs an :meth:`insert`.

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_save():
  ...     coll = db.test_collection
  ...     doc = {'key': 'value'}
  ...     yield motor.Op(coll.save, doc)
  ...     print 'document _id:', repr(doc['_id'])
  ...     doc['other_key'] = 'other_value'
  ...     yield motor.Op(coll.save, doc)
  ...     yield motor.Op(coll.remove, doc)
  ...     IOLoop.instance().stop()
  ...
  >>> do_save()
  >>> IOLoop.instance().start()
  document _id: ObjectId('...')

Removing Documents
------------------

:meth:`~motor.MotorCollection.remove` takes a query with the same syntax as
:meth:`~motor.MotorCollection.find`.
:meth:`remove` immediately removes all matching documents.

.. doctest:: after-inserting-2000-docs

  >>> @gen.engine
  ... def do_remove():
  ...     coll = db.test_collection
  ...     n = yield motor.Op(coll.count)
  ...     print n, 'documents before calling remove()'
  ...     result = yield motor.Op(db.test_collection.remove,
  ...         {'i': {'$gte': 1000}})
  ...     print (yield motor.Op(coll.count)), 'documents after'
  ...     IOLoop.instance().stop()
  ...
  >>> do_remove()
  >>> IOLoop.instance().start()
  2000 documents before calling remove()
  1000 documents after

.. mongodoc:: remove

Commands
--------
Besides the "CRUD" operations--insert, update, remove, and find--all other
operations on MongoDB are commands. Run them using
the :meth:`~motor.MotorDatabase.command` method on :class:`~motor.MotorDatabase`:

.. doctest:: after-inserting-2000-docs

  >>> from bson import SON
  >>> @gen.engine
  ... def use_count_command():
  ...     response = yield motor.Op(
  ...         db.command, SON([("count", "test_collection")]))
  ...     print 'response:', response
  ...     IOLoop.instance().stop()
  ...
  >>> use_count_command()
  >>> IOLoop.instance().start()
  response: {u'ok': 1.0, u'n': 1000.0}

Since the order of command parameters matters, don't use a Python dict to pass
the command's parameters. Instead, make a habit of using :class:`bson.SON`,
from the ``bson`` module included with PyMongo::

    yield motor.Op(
        db.command, SON([("distinct", "test_collection"), ("key", "my_key"]))

Many commands have special helper methods, such as
:meth:`~motor.MotorDatabase.create_collection` or
:meth:`~motor.MotorCollection.aggregate`, but these are just conveniences atop
the basic :meth:`command` method.

.. mongodoc:: commands

Further Reading
---------------
The handful of classes and methods introduced here are sufficient for daily
tasks. The API documentation for :class:`~motor.MotorClient`,
:class:`~motor.MotorReplicaSetClient`, :class:`~motor.MotorDatabase`,
:class:`~motor.MotorCollection`, and :class:`~motor.MotorCursor` provides a
reference to Motor's complete feature set.

Learning to use the MongoDB driver is just the beginning, of course. For
in-depth instruction in MongoDB itself, see `The MongoDB Manual`_.

.. _The MongoDB Manual: http://docs.mongodb.org/manual/

.. [#max_concurrent] ``max_concurrent`` is set when creating a
  :class:`~motor.MotorClient` or :class:`~motor.MotorReplicaSetClient`.
