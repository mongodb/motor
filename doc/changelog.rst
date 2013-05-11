Changelog
=========

Next release
------------

**Changes**

All Motor asynchronous methods (except ``MotorCursor``'s
:meth:`~motor.MotorCursor.each``) now return a `Future
<http://www.tornadoweb.org/documentation/gen.html>`_. The callback argument
to these methods is now optional. If a callback is passed, it will be
executed with the (result, error) of the operation as in Motor 0.1. If no
callback is passed, a Future is returned that resolves to the method's
result or error.

The ``MotorCursor.tail`` method has been removed. It was complex, diverged from
PyMongo's feature set, and encouraged overuse of MongoDB capped collections as
message queues when a purpose-built message queue is more appropriate. An
example of tailing a capped collection is provided:
:doc:`examples/tailable-cursors`.

The ``length`` argument to ``MotorCursor``'s
:meth:`~motor.MotorCursor.to_list`` is no longer optional.

Dropped Python 2.5 support (since Tornado 3.0 has dropped it).

``GridFSHandler``'s :meth:`~motor.web.GridFSHandler.get_gridfs_file` now
returns Future instead of accepting a callback.

**Bugfixes**

``MotorReplicaSetClient.open`` threw an error if called without a callback.

``MotorCursor.to_list`` `ignored SON manipulators
<https://jira.mongodb.org/browse/MOTOR-8>`_. (Thanks to Eren Güven for the
report and the fix.)
