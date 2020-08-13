.. currentmodule:: motor.motor_asyncio

Tutorial: Using Motor With :mod:`asyncio`
=========================================

.. These setups are redundant because I can't figure out how to make doctest
  run a common setup *before* the setup for the two groups. A "testsetup:: *"
  is the obvious answer, but it's run *after* group-specific setup.

.. testsetup:: before-inserting-2000-docs

  import pymongo
  import motor.motor_asyncio
  import asyncio
  db = motor.motor_asyncio.AsyncIOMotorClient().test_database

.. testsetup:: after-inserting-2000-docs

  import pymongo
  import motor.motor_asyncio
  import asyncio
  db = motor.motor_asyncio.AsyncIOMotorClient().test_database
  pymongo.MongoClient().test_database.test_collection.insert_many(
      [{'i': i} for i in range(2000)])

.. testcleanup:: *

  import pymongo
  pymongo.MongoClient().test_database.test_collection.delete_many({})

A guide to using MongoDB and asyncio with Motor.

.. contents::

Tutorial Prerequisites
----------------------
You can learn about MongoDB with the `MongoDB Tutorial`_ before you learn Motor.

Using Python 3.4 or later, do::

  $ python3 -m pip install motor

This tutorial assumes that a MongoDB instance is running on the
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

* :class:`~motor.motor_asyncio.AsyncIOMotorClient`
  represents a mongod process, or a cluster of them. You explicitly create one
  of these client objects, connect it to a running mongod or mongods, and
  use it for the lifetime of your application.
* :class:`~motor.motor_asyncio.AsyncIOMotorDatabase`: Each mongod has a set of databases (distinct
  sets of data files on disk). You can get a reference to a database from a
  client.
* :class:`~motor.motor_asyncio.AsyncIOMotorCollection`: A database has a set of collections, which
  contain documents; you get a reference to a collection from a database.
* :class:`~motor.motor_asyncio.AsyncIOMotorCursor`: Executing :meth:`~motor.motor_asyncio.AsyncIOMotorCollection.find` on
  an :class:`~motor.motor_asyncio.AsyncIOMotorCollection` gets an :class:`~motor.motor_asyncio.AsyncIOMotorCursor`, which
  represents the set of documents matching a query.

Creating a Client
-----------------
You typically create a single instance of :class:`~motor.motor_asyncio.AsyncIOMotorClient` at the time your
application starts up.

.. doctest:: before-inserting-2000-docs

  >>> import motor.motor_asyncio
  >>> client = motor.motor_asyncio.AsyncIOMotorClient()

This connects to a ``mongod`` listening on the default host and port. You can
specify the host and port like:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.motor_asyncio.AsyncIOMotorClient('localhost', 27017)

Motor also supports `connection URIs`_:

.. doctest:: before-inserting-2000-docs

  >>> client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')

Connect to a replica set like:

  >>> client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://host1,host2/?replicaSet=my-replicaset-name')

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

Creating a reference to a database does no I/O and does not require an
``await`` expression.

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
collection does no I/O and doesn't require an ``await`` expression.

Inserting a Document
--------------------
As in PyMongo, Motor represents MongoDB documents with Python dictionaries. To
store a document in MongoDB, call :meth:`~AsyncIOMotorCollection.insert_one` in an
``await`` expression:

.. doctest:: before-inserting-2000-docs

  >>> async def do_insert():
  ...     document = {'key': 'value'}
  ...     result = await db.test_collection.insert_one(document)
  ...     print('result %s' % repr(result.inserted_id))
  ...
  >>>
  >>> import asyncio
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_insert())
  result ObjectId('...')

.. mongodoc:: insert

.. doctest:: before-inserting-2000-docs
  :hide:

  >>> # Clean up from previous insert
  >>> pymongo.MongoClient().test_database.test_collection.delete_many({})
  <pymongo.results.DeleteResult ...>

Insert documents in large batches with :meth:`~AsyncIOMotorCollection.insert_many`:

.. doctest:: before-inserting-2000-docs

  >>> async def do_insert():
  ...     result = await db.test_collection.insert_many(
  ...         [{'i': i} for i in range(2000)])
  ...     print('inserted %d docs' % (len(result.inserted_ids),))
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_insert())
  inserted 2000 docs

Getting a Single Document With `find_one`
-----------------------------------------

Use :meth:`~motor.motor_asyncio.AsyncIOMotorCollection.find_one` to get the first document that
matches a query. For example, to get a document where the value for key "i" is
less than 1:

.. doctest:: after-inserting-2000-docs

  >>> async def do_find_one():
  ...     document = await db.test_collection.find_one({'i': {'$lt': 1}})
  ...     pprint.pprint(document)
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_find_one())
  {'_id': ObjectId('...'), 'i': 0}

The result is a dictionary matching the one that we inserted previously.

.. note:: The returned document contains an ``"_id"``, which was
   automatically added on insert.

.. mongodoc:: find

Querying for More Than One Document
-----------------------------------
Use :meth:`~motor.motor_asyncio.AsyncIOMotorCollection.find` to query for a set of documents.
:meth:`~motor.motor_asyncio.AsyncIOMotorCollection.find` does no I/O and does not require an ``await``
expression. It merely creates an :class:`~motor.motor_asyncio.AsyncIOMotorCursor` instance. The query is
actually executed on the server when you call :meth:`~motor.motor_asyncio.AsyncIOMotorCursor.to_list`
or execute an ``async for`` loop.

To find all documents with "i" less than 5:

.. doctest:: after-inserting-2000-docs

  >>> async def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 5}}).sort('i')
  ...     for document in await cursor.to_list(length=100):
  ...         pprint.pprint(document)
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_find())
  {'_id': ObjectId('...'), 'i': 0}
  {'_id': ObjectId('...'), 'i': 1}
  {'_id': ObjectId('...'), 'i': 2}
  {'_id': ObjectId('...'), 'i': 3}
  {'_id': ObjectId('...'), 'i': 4}

A ``length`` argument is required when you call ``to_list`` to prevent Motor
from buffering an unlimited number of documents.

``async for``
~~~~~~~~~~~~~

You can handle one document at a time in an ``async for`` loop:

.. doctest:: after-inserting-2000-docs

  >>> async def do_find():
  ...     c = db.test_collection
  ...     async for document in c.find({'i': {'$lt': 2}}):
  ...         pprint.pprint(document)
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_find())
  {'_id': ObjectId('...'), 'i': 0}
  {'_id': ObjectId('...'), 'i': 1}

You can apply a sort, limit, or skip to a query before you begin iterating:

.. doctest:: after-inserting-2000-docs

  >>> async def do_find():
  ...     cursor = db.test_collection.find({'i': {'$lt': 4}})
  ...     # Modify the query before iterating
  ...     cursor.sort('i', -1).skip(1).limit(2)
  ...     async for document in cursor:
  ...         pprint.pprint(document)
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_find())
  {'_id': ObjectId('...'), 'i': 2}
  {'_id': ObjectId('...'), 'i': 1}

The cursor does not actually retrieve each document from the server
individually; it gets documents efficiently in `large batches`_.

.. _`large batches`: https://docs.mongodb.com/manual/tutorial/iterate-a-cursor/#cursor-batches

Counting Documents
------------------
Use :meth:`~motor.motor_asyncio.AsyncIOMotorCollection.count_documents` to
determine the number of documents in a collection, or the number of documents
that match a query:

.. doctest:: after-inserting-2000-docs

  >>> async def do_count():
  ...     n = await db.test_collection.count_documents({})
  ...     print('%s documents in collection' % n)
  ...     n = await db.test_collection.count_documents({'i': {'$gt': 1000}})
  ...     print('%s documents where i > 1000' % n)
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_count())
  2000 documents in collection
  999 documents where i > 1000

Updating Documents
------------------

:meth:`~motor.motor_asyncio.AsyncIOMotorCollection.replace_one` changes a document. It requires two
parameters: a *query* that specifies which document to replace, and a
replacement document. The query follows the same syntax as for :meth:`find` or
:meth:`find_one`. To replace a document:

.. doctest:: after-inserting-2000-docs

  >>> async def do_replace():
  ...     coll = db.test_collection
  ...     old_document = await coll.find_one({'i': 50})
  ...     print('found document: %s' % pprint.pformat(old_document))
  ...     _id = old_document['_id']
  ...     result = await coll.replace_one({'_id': _id}, {'key': 'value'})
  ...     print('replaced %s document' % result.modified_count)
  ...     new_document = await coll.find_one({'_id': _id})
  ...     print('document is now %s' % pprint.pformat(new_document))
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_replace())
  found document: {'_id': ObjectId('...'), 'i': 50}
  replaced 1 document
  document is now {'_id': ObjectId('...'), 'key': 'value'}

You can see that :meth:`replace_one` replaced everything in the old document
except its ``_id`` with the new document.

Use :meth:`~motor.motor_asyncio.AsyncIOMotorCollection.update_one` with MongoDB's modifier operators to
update part of a document and leave the
rest intact. We'll find the document whose "i" is 51 and use the ``$set``
operator to set "key" to "value":

.. doctest:: after-inserting-2000-docs

  >>> async def do_update():
  ...     coll = db.test_collection
  ...     result = await coll.update_one({'i': 51}, {'$set': {'key': 'value'}})
  ...     print('updated %s document' % result.modified_count)
  ...     new_document = await coll.find_one({'i': 51})
  ...     print('document is now %s' % pprint.pformat(new_document))
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_update())
  updated 1 document
  document is now {'_id': ObjectId('...'), 'i': 51, 'key': 'value'}

"key" is set to "value" and "i" is still 51.

:meth:`update_one` only affects the first document it finds, you can
update all of them with :meth:`update_many`::

    await coll.update_many({'i': {'$gt': 100}},
                           {'$set': {'key': 'value'}})

.. mongodoc:: update

Deleting Documents
------------------

:meth:`~motor.motor_asyncio.AsyncIOMotorCollection.delete_many` takes a query with the same syntax as
:meth:`~motor.motor_asyncio.AsyncIOMotorCollection.find`.
:meth:`delete_many` immediately removes all matching documents.

.. doctest:: after-inserting-2000-docs

  >>> async def do_delete_many():
  ...     coll = db.test_collection
  ...     n = await coll.count_documents({})
  ...     print('%s documents before calling delete_many()' % n)
  ...     result = await db.test_collection.delete_many({'i': {'$gte': 1000}})
  ...     print('%s documents after' % (await coll.count_documents({})))
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(do_delete_many())
  2000 documents before calling delete_many()
  1000 documents after

.. mongodoc:: remove

Commands
--------
All operations on MongoDB are implemented internally as commands. Run them using
the :meth:`~motor.motor_asyncio.AsyncIOMotorDatabase.command` method on
:class:`~motor.motor_asyncio.AsyncIOMotorDatabase`::

.. doctest:: after-inserting-2000-docs

  >>> from bson import SON
  >>> async def use_distinct_command():
  ...     response = await db.command(SON([("distinct", "test_collection"),
  ...                                      ("key", "i")]))
  ...
  >>> loop = asyncio.get_event_loop()
  >>> loop.run_until_complete(use_distinct_command())

Since the order of command parameters matters, don't use a Python dict to pass
the command's parameters. Instead, make a habit of using :class:`bson.SON`,
from the ``bson`` module included with PyMongo.

Many commands have special helper methods, such as
:meth:`~motor.motor_asyncio.AsyncIOMotorDatabase.create_collection` or
:meth:`~motor.motor_asyncio.AsyncIOMotorCollection.aggregate`, but these are just conveniences atop
the basic :meth:`command` method.

.. mongodoc:: commands

.. _example-web-application-aiohttp:

A Web Application With `aiohttp`_
---------------------------------

Let us create a web application using `aiohttp`_, a popular HTTP package for
asyncio. Install it with::

  python3 -m pip install aiohttp

We are going to make a trivial web site with two pages served from MongoDB.
To begin:

.. literalinclude:: examples/aiohttp_example.py
  :language: python3
  :start-after: setup-start
  :end-before: setup-end

The ``AsyncIOMotorClient`` constructor does not actually connect to MongoDB.
The client connects on demand, when you attempt the first operation.
We create it and assign the "test" database's handle to ``db``.

The ``setup_db`` coroutine drops the "pages" collection (plainly, this code is
for demonstration purposes), then inserts two documents. Each document's page
name is its unique id, and the "body" field is a simple HTML page. Finally,
``setup_db`` returns the database handle.

We'll use the ``setup_db`` coroutine soon. First, we need a request handler
that serves pages from the data we stored in MongoDB.

.. literalinclude:: examples/aiohttp_example.py
  :language: python3
  :start-after: handler-start
  :end-before: handler-end

We start the server by running ``setup_db`` and passing the database handle
to an :class:`aiohttp.web.Application`:

.. literalinclude:: examples/aiohttp_example.py
  :language: python3
  :start-after: main-start
  :end-before: main-end

Note that it is a common mistake to create a new client object for every
request; this comes at a dire performance cost. Create the client
when your application starts and reuse that one client for the lifetime
of the process. You can maintain the client by storing a database handle
from the client on your application object, as shown in this example.

Visit ``localhost:8080/pages/page-one`` and the server responds "Hello!".
At ``localhost:8080/pages/page-two`` it responds "Goodbye." At other URLs it
returns a 404.

The complete code is in the Motor repository in ``examples/aiohttp_example.py``.

.. _aiohttp: https://aiohttp.readthedocs.io/

See also the :doc:`examples/aiohttp_gridfs_example`.

Further Reading
---------------
The handful of classes and methods introduced here are sufficient for daily
tasks. The API documentation for :class:`~motor.motor_asyncio.AsyncIOMotorClient`, :class:`~motor.motor_asyncio.AsyncIOMotorDatabase`,
:class:`~motor.motor_asyncio.AsyncIOMotorCollection`, and :class:`~motor.motor_asyncio.AsyncIOMotorCursor` provides a
reference to Motor's complete feature set.

Learning to use the MongoDB driver is just the beginning, of course. For
in-depth instruction in MongoDB itself, see `The MongoDB Manual`_.

.. _The MongoDB Manual: http://docs.mongodb.org/manual/

