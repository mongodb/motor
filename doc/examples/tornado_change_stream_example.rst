.. _tornado_change_stream_example:

Tornado Change Stream Example
=============================

.. currentmodule:: motor.motor_tornado

Watch a collection for changes with :meth:`MotorCollection.watch` and display
each change notification on a web page using web sockets. 

Instructions
------------

Start a MongoDB server on its default port and run this script. Then visit:

http://localhost:8888

Open a ``mongo`` shell in the terminal and perform some operations on the
"test" collection in the "test" database:

.. code-block:: none

  > use test
  switched to db test
  > db.test.insertOne({})
  > db.test.updateOne({}, {$set: {x: 1}})
  > db.test.deleteOne({})

The application receives each change notification and displays it as JSON on
the web page:

.. code-block:: none

  Changes

  {'documentKey': {'_id': ObjectId('5a2a6967ea2dcf7b1c721cfb')},
   'fullDocument': {'_id': ObjectId('5a2a6967ea2dcf7b1c721cfb')},
   'ns': {'coll': 'test', 'db': 'test'},
   'operationType': 'insert'}

  {'documentKey': {'_id': ObjectId('5a2a6967ea2dcf7b1c721cfb')},
   'ns': {'coll': 'test', 'db': 'test'},
   'operationType': 'update',
   'updateDescription': {'removedFields': [], 'updatedFields': {'x': 1.0}}}

  {'documentKey': {'_id': ObjectId('5a2a6967ea2dcf7b1c721cfb')},
   'ns': {'coll': 'test', 'db': 'test'},
   'operationType': 'delete'}

Display change notifications over a web socket
----------------------------------------------

.. literalinclude:: tornado_change_stream_example.py
  :language: python3
