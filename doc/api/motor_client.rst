:class:`MotorClient` -- Connection to MongoDB
=================================================

.. currentmodule:: motor

.. autoclass:: MotorClient
  :members:

  .. automethod:: disconnect

  .. describe:: c[db_name] || c.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorClient` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
     Raises :class:`~pymongo.errors.InvalidOperation` if connection isn't opened yet.
