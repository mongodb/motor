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

Authentication at Startup
-------------------------
To create an authenticated connection use a `MongoDB connection URI`_::

    uri = "mongodb://user:pass@localhost:27017/database_name"
    client = motor.motor_tornado.MotorClient(uri)

Motor logs in to the server on demand, when you first attempt an operation.

Asynchronous Authentication
---------------------------
Use the non-blocking :meth:`~MotorDatabase.authenticate` method to log
in after starting the IOLoop::

    client = motor.motor_tornado.MotorClient('localhost', 27017)

    @gen.coroutine
    def login(c):
        yield c.my_database.authenticate("user", "pass")

After you've logged in to a database with a given :class:`MotorClient`, all further
operations on that database using that client will already be authenticated
until you call :meth:`~MotorDatabase.logout`.

.. _MongoDB connection URI: http://docs.mongodb.org/manual/reference/connection-string/
