:class:`~motor.motor_asyncio.AsyncIOMotorCollection`
====================================================

.. currentmodule:: motor.motor_asyncio

.. autoclass:: AsyncIOMotorCollection
  :members:

  .. describe:: c[name] || c.name

     Get the `name` sub-collection of :class:`AsyncIOMotorCollection` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid
     collection name is used.

  .. attribute:: database

  The :class:`AsyncIOMotorDatabase` that this
  :class:`AsyncIOMotorCollection` is a part of.
