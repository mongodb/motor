.. currentmodule:: motor.motor_tornado

Authentication With Motor
=========================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver. Critical bug fixes will be made until May 14th, 2027.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.


This page describes using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

To use authentication, you must start ``mongod`` with ``--auth`` or, for
replica sets or sharded clusters, ``--keyFile``. Create an admin user and
optionally normal users or read-only users.

.. seealso:: `MongoDB Authentication
  <https://mongodb.com/docs/manual/tutorial/control-access-to-mongodb-with-authentication/>`_

To create an authenticated connection use a `MongoDB connection URI`_::

    uri = "mongodb://user:pass@localhost:27017/database_name"
    client = motor.motor_tornado.MotorClient(uri)

Motor logs in to the server on demand, when you first attempt an operation.

.. _MongoDB connection URI: https://mongodb.com/docs/manual/reference/connection-string/
