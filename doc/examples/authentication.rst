.. currentmodule:: motor.motor_tornado

Authentication With Motor
=========================

This page describes using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

To use authentication, you must start ``mongod`` with ``--auth`` or, for
replica sets or sharded clusters, ``--keyFile``. Create an admin user and
optionally normal users or read-only users.

.. seealso:: `MongoDB Authentication
  <http://docs.mongodb.org/manual/tutorial/control-access-to-mongodb-with-authentication/>`_

To create an authenticated connection use a `MongoDB connection URI`_::

    uri = "mongodb://user:pass@localhost:27017/database_name"
    client = motor.motor_tornado.MotorClient(uri)

Motor logs in to the server on demand, when you first attempt an operation.

.. _MongoDB connection URI: http://docs.mongodb.org/manual/reference/connection-string/
