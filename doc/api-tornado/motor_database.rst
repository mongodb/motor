:class:`~motor.motor_tornado.MotorDatabase`
===========================================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. currentmodule:: motor.motor_tornado

.. autoclass:: MotorDatabase
  :members:

  .. describe:: db[collection_name] || db.collection_name

     Get the `collection_name` :class:`MotorCollection` of
     :class:`MotorDatabase` `db`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid collection name is used.
