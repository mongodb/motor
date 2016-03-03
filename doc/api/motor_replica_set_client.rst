:class:`~motor.motor_tornado.MotorReplicaSetClient` -- Connection to MongoDB replica set
========================================================================================

.. currentmodule:: motor.motor_tornado

.. autoclass:: motor.motor_tornado.MotorReplicaSetClient
  :members:

  .. describe:: client[db_name] || client.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorReplicaSetClient` `client`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
