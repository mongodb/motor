:class:`~motor.motor_asyncio.AsyncIOMotorDatabase`
==================================================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. currentmodule:: motor.motor_asyncio

.. autoclass:: AsyncIOMotorDatabase
  :members:

  .. describe:: db[collection_name] || db.collection_name

     Get the `collection_name` :class:`AsyncIOMotorCollection` of
     :class:`AsyncIOMotorDatabase` `db`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid collection name is used.
