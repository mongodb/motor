.. currentmodule:: motor.motor_tornado

Bulk Write Operations
=====================

.. testsetup::

  client = MotorClient()
  db = client.test_database
  IOLoop.current().run_sync(db.test.drop)

This tutorial explains how to take advantage of Motor's bulk
write operation features. Executing write operations in batches
reduces the number of network round trips, increasing write
throughput.

This example describes using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

Bulk Insert
-----------

A batch of documents can be inserted by passing a list or generator
to the :meth:`~MotorCollection.insert_many` method. Motor
will automatically split the batch into smaller sub-batches based on
the maximum message size accepted by MongoDB, supporting very large
bulk insert operations.

.. doctest::

  >>> @gen.coroutine
  ... def f():
  ...     yield db.test.insert_many(({'i': i} for i in range(10000)))
  ...     count = yield db.test.count()
  ...     print("Final count: %d" % count)
  >>>
  >>> IOLoop.current().run_sync(f)
  Final count: 10000

Mixed Bulk Write Operations
---------------------------

.. versionadded:: 0.2

Motor also supports executing mixed bulk write operations. A batch
of insert, update, and delete operations can be executed together using
the Bulk API.

.. _ordered_bulk:

Ordered Bulk Write Operations
.............................

Ordered bulk write operations are batched and sent to the server in the
order provided for serial execution. The return value is a document
describing the type and count of operations performed.

.. doctest::

  >>> from pprint import pprint
  >>>
  >>> @gen.coroutine
  ... def f():
  ...    bulk = db.test.initialize_ordered_bulk_op()
  ...    # Remove all documents from the previous example.
  ...    bulk.find({}).remove()
  ...    bulk.insert({'_id': 1})
  ...    bulk.insert({'_id': 2})
  ...    bulk.insert({'_id': 3})
  ...    bulk.find({'_id': 1}).update({'$set': {'foo': 'bar'}})
  ...    bulk.find({'_id': 4}).upsert().update({'$inc': {'j': 1}})
  ...    bulk.find({'j': 1}).replace_one({'j': 2})
  ...    result = yield bulk.execute()
  ...    pprint(result)
  ...
  >>> IOLoop.current().run_sync(f)
  {'nInserted': 3,
   'nMatched': 2,
   'nModified': 2,
   'nRemoved': 10000,
   'nUpserted': 1,
   'upserted': [{'_id': 4, 'index': 5}],
   'writeConcernErrors': [],
   'writeErrors': []}

The first write failure that occurs (e.g. duplicate key error) aborts the
remaining operations, and Motor raises :class:`~pymongo.errors.BulkWriteError`.
The :attr:`details` attibute of the exception instance provides the execution
results up until the failure occurred and details about the failure - including
the operation that caused the failure.

.. doctest::

  >>> from pymongo.errors import BulkWriteError
  >>>
  >>> @gen.coroutine
  ... def f():
  ...     bulk = db.test.initialize_ordered_bulk_op()
  ...     bulk.find({'j': 2}).replace_one({'i': 5})
  ...     # Violates the unique key constraint on _id.
  ...
  ...     bulk.insert({'_id': 4})
  ...     bulk.find({'i': 5}).remove_one()
  ...     try:
  ...         yield bulk.execute()
  ...     except BulkWriteError as err:
  ...         pprint(err.details)
  ... 
  >>> IOLoop.current().run_sync(f)
  {'nInserted': 0,
   'nMatched': 1,
   'nModified': 1,
   'nRemoved': 0,
   'nUpserted': 0,
   'upserted': [],
   'writeConcernErrors': [],
   'writeErrors': [{'code': 11000,
                    'errmsg': '... duplicate key error ...',
                    'index': 1,
                    'op': {'_id': 4}}]}

.. _unordered_bulk:

Unordered Bulk Write Operations
...............................

Unordered bulk write operations are batched and sent to the server in
**arbitrary order** where they may be executed in parallel. Any errors
that occur are reported after all operations are attempted.

In the next example the first and third operations fail due to the unique
constraint on _id. Since we are doing unordered execution the second
and fourth operations succeed.

.. doctest::

  >>> @gen.coroutine
  ... def f():
  ...     bulk = db.test.initialize_unordered_bulk_op()
  ...     bulk.insert({'_id': 1})
  ...     bulk.find({'_id': 2}).remove_one()
  ...     bulk.insert({'_id': 3})
  ...     bulk.find({'_id': 4}).replace_one({'i': 1})
  ...     try:
  ...         yield bulk.execute()
  ...     except BulkWriteError as err:
  ...         pprint(err.details)
  ... 
  >>> IOLoop.current().run_sync(f)
  {'nInserted': 0,
   'nMatched': 1,
   'nModified': 1,
   'nRemoved': 1,
   'nUpserted': 0,
   'upserted': [],
   'writeConcernErrors': [],
   'writeErrors': [{'code': 11000,
                    'errmsg': '... duplicate key error ...',
                    'index': 0,
                    'op': {'_id': 1}},
                   {'code': 11000,
                    'errmsg': '... duplicate key error ...',
                    'index': 2,
                    'op': {'_id': 3}}]}

Write Concern
.............

By default bulk operations are executed with the
:meth:`~MotorCollection.write_concern` of the collection they are
executed against, typically the default write concern ``{w: 1}``. A custom
write concern can be passed to the
:meth:`~MotorBulkOperationBuilder.execute` method. Write concern
errors (e.g. wtimeout) will be reported after all operations are attempted,
regardless of execution order.

.. doctest::
  :options: +SKIP

  .. Standalone MongoDB raises "can't use w>1" with this example, so skip it.

  >>> @gen.coroutine
  ... def f():
  ...     bulk = db.test.initialize_ordered_bulk_op()
  ...     bulk.insert({'a': 0})
  ...     bulk.insert({'a': 1})
  ...     bulk.insert({'a': 2})
  ...     bulk.insert({'a': 3})
  ...     try:
  ...         # Times out if the replica set has fewer than four members.
  ...         yield bulk.execute({'w': 4, 'wtimeout': 1})
  ...     except BulkWriteError as err:
  ...         pprint(err.details)
  ... 
  >>> IOLoop.current().run_sync(f)
  {'nInserted': 4,
   'nMatched': 0,
   'nModified': 0,
   'nRemoved': 0,
   'nUpserted': 0,
   'upserted': [],
   'writeConcernErrors': [{'code': 64,
                           'errInfo': {'wtimeout': True},
                           'errmsg': 'waiting for replication timed out'}],
   'writeErrors': []}
