:class:`~motor.motor_tornado.MotorCollection`
=============================================

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
