.. currentmodule:: motor.motor_tornado

.. _bulk-write-tutorial:

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

  >>> async def f():
  ...     await db.test.insert_many(({'i': i} for i in range(10000)))
  ...     count = await db.test.count_documents({})
  ...     print("Final count: %d" % count)
  >>>
  >>> IOLoop.current().run_sync(f)
  Final count: 10000

Mixed Bulk Write Operations
---------------------------

Motor also supports executing mixed bulk write operations. A batch
of insert, update, and remove operations can be executed together using
the bulk write operations API.

.. _ordered_bulk:

Ordered Bulk Write Operations
.............................

Ordered bulk write operations are batched and sent to the server in the
order provided for serial execution. The return value is an instance of
:class:`~pymongo.results.BulkWriteResult` describing the type and count
of operations performed.

.. doctest::
  :options: +NORMALIZE_WHITESPACE

  >>> from pprint import pprint
  >>> from pymongo import InsertOne, DeleteMany, ReplaceOne, UpdateOne
  >>> async def f():
  ...     result = await db.test.bulk_write([
  ...     DeleteMany({}),  # Remove all documents from the previous example.
  ...     InsertOne({'_id': 1}),
  ...     InsertOne({'_id': 2}),
  ...     InsertOne({'_id': 3}),
  ...     UpdateOne({'_id': 1}, {'$set': {'foo': 'bar'}}),
  ...     UpdateOne({'_id': 4}, {'$inc': {'j': 1}}, upsert=True),
  ...     ReplaceOne({'j': 1}, {'j': 2})])
  ...     pprint(result.bulk_api_result)
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
remaining operations, and Motor raises
:class:`~pymongo.errors.BulkWriteError`. The :attr:`details` attribute of
the exception instance provides the execution results up until the failure
occurred and details about the failure - including the operation that caused
the failure.

.. doctest::
  :options: +NORMALIZE_WHITESPACE

  >>> from pymongo import InsertOne, DeleteOne, ReplaceOne
  >>> from pymongo.errors import BulkWriteError
  >>> async def f():
  ...     requests = [
  ...         ReplaceOne({'j': 2}, {'i': 5}),
  ...         InsertOne({'_id': 4}),  # Violates the unique key constraint on _id.
  ...         DeleteOne({'i': 5})]
  ...     try:
  ...         await db.test.bulk_write(requests)
  ...     except BulkWriteError as bwe:
  ...         pprint(bwe.details)
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
  :options: +NORMALIZE_WHITESPACE

  >>> async def f():
  ...     requests = [
  ...         InsertOne({'_id': 1}),
  ...         DeleteOne({'_id': 2}),
  ...         InsertOne({'_id': 3}),
  ...         ReplaceOne({'_id': 4}, {'i': 1})]
  ...     try:
  ...         await db.test.bulk_write(requests, ordered=False)
  ...     except BulkWriteError as bwe:
  ...         pprint(bwe.details)
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

Bulk operations are executed with the
:attr:`~pymongo.collection.Collection.write_concern` of the collection they
are executed against. Write concern errors (e.g. wtimeout) will be reported
after all operations are attempted, regardless of execution order.

.. doctest::
  :options: +SKIP

  .. Standalone MongoDB raises "can't use w>1" with this example, so skip it.

  >>> from pymongo import WriteConcern
  >>> async def f():
  ...     coll = db.get_collection(
  ...         'test', write_concern=WriteConcern(w=4, wtimeout=1))
  ...     try:
  ...         await coll.bulk_write([InsertOne({'a': i}) for i in range(4)])
  ...     except BulkWriteError as bwe:
  ...         pprint(bwe.details)
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
