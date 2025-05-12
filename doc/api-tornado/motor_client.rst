:class:`~motor.motor_tornado.MotorClient` -- Connection to MongoDB
==================================================================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. currentmodule:: motor.motor_tornado

.. autoclass:: MotorClient
  :members:

  .. describe:: client[db_name] || client.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorClient` `client`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
