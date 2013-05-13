Changelog
=========

.. currentmodule:: motor

Motor 0.2
---------

**Changes**

Motor 0.2 now requires Tornado 3. However, the previous version, Motor 0.1, is
still available for Tornado 2 users.

Motor 0.2 drops Python 2.5 support (since Tornado 3 has dropped it).

All Motor asynchronous methods (except
:meth:`MotorCursor.each`) now return a `Future
<http://tornadoweb.org/en/stable/gen.html>`_. The callback argument
to these methods is now optional. If a callback is passed, it will be
executed with the (result, error) of the operation as in Motor 0.1. If no
callback is passed, a Future is returned that resolves to the method's
result or error.

The ``length`` argument to :meth:`MotorCursor.to_list` is no longer optional.

The ``MotorCursor.tail`` method has been removed. It was complex, diverged from
PyMongo's feature set, and encouraged overuse of MongoDB capped collections as
message queues when a purpose-built message queue is more appropriate. An
example of tailing a capped collection is provided:
:doc:`examples/tailable-cursors`.

``MotorClient.is_locked`` has been removed since calling it from Motor would be
bizarre. See "Migration" below for a workaround.

:meth:`~web.GridFSHandler.get_gridfs_file` now
returns Future instead of accepting a callback.

**Migration**

``motor.Op`` is deprecated. You can continue to use it, but the simpler
syntax yielding a Future is preferred::

    document = yield collection.find_one()

Code that uses explicit callbacks with Motor 0.2 works the same as in Motor
0.1.

Any calls to :meth:`MotorCursor.to_list` that omitted the ``length``
argument must now include it::

    result = yield collection.find().to_list(100)

:meth:`MotorClient.is_locked` has been removed. If you called it like::

    locked = yield motor.Op(client.is_locked)

you should now do::

    result = yield client.admin.current_op()
    locked = bool(result.get('fsyncLock', None))

**Bugfixes**

``MotorReplicaSetClient.open`` threw an error if called without a callback.

``MotorCursor.to_list`` `ignored SON manipulators
<https://jira.mongodb.org/browse/MOTOR-8>`_. (Thanks to Eren Güven for the
report and the fix.)
