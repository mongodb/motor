Authentication With Motor
=========================

To use authentication, you must start ``mongod`` with ``--auth`` or, for
replica sets or sharded clusters, ``--keyFile``. Create an admin user and
optionally normal users or read-only users.

.. seealso:: `MongoDB Authentication
  <http://docs.mongodb.org/manual/tutorial/control-access-to-mongodb-with-authentication/>`_

Authentication at Startup
-------------------------
To create an authenticated connection use a `MongoDB connection URI`_::

    uri = "mongodb://user:pass@localhost:27017/database_name"
    client = motor.MotorClient(uri)

Motor logs in to the server on demand, when you first attempt an operation.

Asynchronous Authentication
---------------------------
Use the non-blocking :meth:`~motor.core.MotorDatabase.authenticate` method to log
in after starting the IOLoop::

    client = motor.MotorClient('localhost', 27017)

    @gen.coroutine
    def login(c):
        yield c.my_database.authenticate("user", "pass")

After you've logged in to a database with a given :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient`, all further operations on that
database using that client will already be authenticated until you
call :meth:`~motor.core.MotorDatabase.logout`.

.. _MongoDB connection URI: http://docs.mongodb.org/manual/reference/connection-string/
