Changelog
=========

.. currentmodule:: motor

Motor 0.2
---------

Changes
~~~~~~~

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

:class:`MotorPool` has been rewritten, both to support the same new features
as the new PyMongo 2.6 Pool, and to stop subclassing PyMongo's Pool to protect
Motor somewhat from PyMongo changes.

:class:`MotorClient` and :class:`MotorReplicaSetClient` no longer support the
``max_concurrent`` option; ``max_pool_size`` has taken on the function of
``max_concurrent`` and the default ``max_pool_size`` is bumped from 10 to 100.
``max_wait_time`` is replaced by ``waitQueueTimeoutMS`` and
``waitQueueMultiple``. Timeouts raise a PyMongo :exc:`ConnectionFailure`;
:exc:`MotorPoolTimeout` is gone.

The ``MotorCursor.tail`` method has been removed. It was complex, diverged from
PyMongo's feature set, and encouraged overuse of MongoDB capped collections as
message queues when a purpose-built message queue is more appropriate. An
example of tailing a capped collection is provided:
:doc:`examples/tailable-cursors`.

``MotorClient.is_locked`` has been removed since calling it from Motor would be
bizarre. See "Migration" below for a workaround.

WaitOp, WaitAllOps

:meth:`~web.GridFSHandler.get_gridfs_file` now
returns Future instead of accepting a callback.

Migration
~~~~~~~~~

Futures
'''''''

``motor.Op`` is deprecated. You can continue to use it, but the simpler
syntax yielding a Future is preferred::

    document = yield collection.find_one()

Code that uses explicit callbacks with Motor 0.2 works the same as in Motor
0.1::

    def callback(document, error):
        if error:
            logging.error("Oh no!")
        else:
            print document

    collection.find_one(callback=callback)

Pool options
''''''''''''

Recently, PyMongo 2.6 updated its connection pooling options. Motor's options
have changed for increased consistency with PyMongo.

:class:`MotorClient` and :class:`MotorReplicaSetClient` have an option
``max_pool_size``, which meant "minimum idle sockets to keep open", but its
meaning has changed to "maximum sockets open per host." Once this limit is
reached, operations will pause waiting for a socket to become available.
Therefore the default has been raised from 10 to 100. If you pass a value for
``max_pool_size`` make sure it's large enough for the expected load. (Sockets
are only opened when needed, so there's no cost to having a ``max_pool_size``
larger than necessary. Err towards a larger value.) If you've been accepting
the default, continue to do so.

The ``max_concurrent`` option is removed, since ``max_pool_size`` now fulfills
the same purpose. If you passed this option, you can remove it or rename to
``max_pool_size``.

``max_wait_time`` has been renamed ``waitQueueTimeoutMS`` for consistency with
PyMongo. If you pass ``max_wait_time``, rename it and multiply by 1000.

The :exc:`MotorPoolTimeout` exception is gone; catch PyMongo's
:exc:`ConnectionFailure` instead.

to_list
'''''''

Any calls to :meth:`MotorCursor.to_list` that omitted the ``length``
argument must now include it::

    result = yield collection.find().to_list(100)

tail
''''

If you relied on ``MotorCursor.tail``, see :doc:`examples/tailable-cursors`
for an example of tailing a capped collection with Motor using a coroutine.

is_locked
'''''''''

If you called ``MotorClient.is_locked`` like::

    locked = yield motor.Op(client.is_locked)

you should now do::

    result = yield client.admin.current_op()
    locked = bool(result.get('fsyncLock', None))

Bugfixes
~~~~~~~~

``MotorReplicaSetClient.open`` threw an error if called without a callback.

``MotorCursor.to_list`` `ignored SON manipulators
<https://jira.mongodb.org/browse/MOTOR-8>`_. (Thanks to Eren Güven for the
report and the fix.)
