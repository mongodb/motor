
.. _timeout-example:

Client Side Operation Timeout
=============================

PyMongo 4.2 introduced :meth:`~pymongo.timeout` and the ``timeoutMS``
URI and keyword argument to :class:`~pymongo.mongo_client.MongoClient`.
These features allow applications to more easily limit the amount of time that
one or more operations can execute before control is returned to the app. This
timeout applies to all of the work done to execute the operation, including
but not limited to server selection, connection checkout, serialization, and
server-side execution.

:meth:`~pymongo.timeout` is asyncio safe; the timeout only applies to current
Task and multiple Tasks can configure different timeouts concurrently.
:meth:`~pymongo.timeout` can be used identically in Motor 3.1+.

For more information and troubleshooting, see the PyMongo docs on
`Client Side Operation Timeout`_.

.. _Client Side Operation Timeout: https://pymongo.readthedocs.io/en/stable/examples/timeouts.html


Basic Usage
-----------

The following example uses :meth:`~pymongo.timeout` to configure a 10-second
timeout for an :meth:`~pymongo.collection.Collection.insert_one` operation::

  import pymongo
  import motor.motor_asyncio
  client = motor.motor_asyncio.AsyncIOMotorClient()
  coll = client.test.test
  with pymongo.timeout(10):
      await coll.insert_one({"name": "Nunu"})

The :meth:`~pymongo.timeout` applies to all pymongo operations within the block.
The following example ensures that both the ``insert`` and the ``find`` complete
within 10 seconds total, or raise a timeout error::

  with pymongo.timeout(10):
      await coll.insert_one({"name": "Nunu"})
      await coll.find_one({"name": "Nunu"})

When nesting :func:`~pymongo.timeout`, the nested deadline is capped by the outer
deadline. The deadline can only be shortened, not extended.
When exiting the block, the previous deadline is restored::

  with pymongo.timeout(5):
      await coll.find_one()  # Uses the 5 second deadline.
      with pymongo.timeout(3):
          await coll.find_one() # Uses the 3 second deadline.
      await coll.find_one()  # Uses the original 5 second deadline.
      with pymongo.timeout(10):
          await coll.find_one()  # Still uses the original 5 second deadline.
      await coll.find_one()  # Uses the original 5 second deadline.

Timeout errors
--------------

When the :meth:`~pymongo.timeout` with-statement is entered, a deadline is set
for the entire block. When that deadline is exceeded, any blocking pymongo operation
will raise a timeout exception. For example::

  try:
      with pymongo.timeout(10):
          await coll.insert_one({"name": "Nunu"})
          await asyncio.sleep(10)
          # The deadline has now expired, the next operation will raise
          # a timeout exception.
          await coll.find_one({"name": "Nunu"})
  except PyMongoError as exc:
      if exc.timeout:
          print(f"block timed out: {exc!r}")
      else:
          print(f"failed with non-timeout error: {exc!r}")

The :attr:`pymongo.errors.PyMongoError.timeout` property (added in PyMongo 4.2)
will be ``True`` when the error was caused by a timeout and ``False`` otherwise.
