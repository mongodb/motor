:class:`~motor.motor_tornado.MotorClient` -- Connection to MongoDB
==================================================================

.. currentmodule:: motor.motor_tornado

.. autoclass:: MotorClient
  :members:

  .. describe:: client[db_name] || client.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorClient` `client`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
