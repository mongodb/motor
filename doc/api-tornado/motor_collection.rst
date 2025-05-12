:class:`~motor.motor_tornado.MotorCollection`
=============================================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. currentmodule:: motor.motor_tornado

.. autoclass:: MotorCollection
  :members:

  .. describe:: c[name] || c.name

     Get the `name` sub-collection of :class:`MotorCollection` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid
     collection name is used.

  .. attribute:: database

  The :class:`MotorDatabase` that this
  :class:`MotorCollection` is a part of.
