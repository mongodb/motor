:class:`~motor.motor_asyncio.AsyncIOMotorDatabase`
==================================================

.. currentmodule:: motor.motor_asyncio

.. autoclass:: AsyncIOMotorDatabase
  :members:

  .. describe:: db[collection_name] || db.collection_name

     Get the `collection_name` :class:`AsyncIOMotorCollection` of
     :class:`AsyncIOMotorDatabase` `db`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid collection name is used.
