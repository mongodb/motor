:class:`~motor.motor_asyncio.AsyncIOMotorClient` -- Connection to MongoDB
=========================================================================

.. autoclass:: motor.motor_asyncio.AsyncIOMotorClient
  :members:

  .. describe:: client[db_name] || client.db_name

     Get the `db_name` :class:`AsyncIOMotorDatabase` on :class:`AsyncIOMotorClient` `client`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
