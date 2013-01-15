Motor Authentication Examples
=============================

To use authentication, you must start ``mongod`` with ``--auth`` or, for
replica sets or sharded clusters, ``--keyFile``.

.. mongodoc:: authenticate

Creating an admin user
----------------------
The first step to securing a MongoDB instance with authentication is to create
a user in the ``admin`` database--this user is like a super-user who can add
or remove regular users::

    from tornado import gen
    import motor

    c = motor.MotorClient().open_sync()

    @gen.engine
    def create_admin_user():
        yield motor.Op(c.admin.add_user, "admin", "secret password")

.. seealso:: :meth:`~motor.MotorDatabase.add_user`

Creating a regular user
-----------------------
Once you've created the admin user you must log in before any further
operations, including creating a regular user::

    @gen.engine
    def create_regular_user():
        yield motor.Op(c.admin.authenticate, "admin", "secret password")
        yield motor.Op(c.my_database.add_user, "jesse", "jesse's password")

.. seealso:: :meth:`~motor.MotorDatabase.authenticate`,
  :meth:`~motor.MotorDatabase.add_user`

Authenticating as a regular user
--------------------------------
Creating an admin user or authenticating as one is a rare task, and typically
done with the mongo shell rather than with Motor. Your day-to-day operations
will only need regular authentication::

    @gen.engine
    def login(c):
        yield motor.Op(c.my_database.authenticate, "jesse", "jesse's password")

After you've logged in to a database with a given :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient`, all further operations on that
database using that client will already be authenticated until you
call :meth:`~motor.MotorDatabase.logout`.

.. seealso:: :meth:`~motor.MotorDatabase.authenticate`,
  :meth:`~motor.MotorDatabase.logout`
