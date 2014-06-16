Changelog
=========

.. currentmodule:: motor

Motor 0.3
---------

No new features.

* Updates PyMongo dependency from 2.7 to 2.7.1,
  therefore inheriting `PyMongo 2.7.1's bug fixes
  <https://jira.mongodb.org/browse/PYTHON/fixforversion/13823>`_.
* Motor continues to support Python 2.6, 2.7, 3.3, and 3.4,
  but now with single-source.
  2to3 no longer runs during installation with Python 3.
* `nosetests` is no longer required for regular Motor tests.

Motor 0.2.1
-----------

Fixes two bugs:

* `MOTOR-32 <https://jira.mongodb.org/browse/MOTOR-32>`_:
  The documentation for :meth:`MotorCursor.close` claimed it immediately
  halted execution of :meth:`MotorCursor.each`, but it didn't.
* `MOTOR-33 <https://jira.mongodb.org/browse/MOTOR-33>`_:
  An incompletely iterated cursor's ``__del__`` method sometimes got stuck
  and cost 100% CPU forever, even though the application was still responsive.

Motor 0.2
---------

This version includes API changes that break backward compatibility
with applications written for Motor 0.1. For most applications, the migration
chores will be minor. In exchange, Motor 0.2 offers a cleaner style, and
it wraps the new and improved PyMongo 2.7 instead of 2.5.

Changes in Dependencies
~~~~~~~~~~~~~~~~~~~~~~~

Motor now requires PyMongo 2.7.0 exactly and Tornado 3 or later. It drops
support for Python 2.5 since Tornado 3 has dropped it.

Motor continues to work with Python 2.6 through 3.4. It still requires
`Greenlet`_.

API Changes
~~~~~~~~~~~

open_sync
'''''''''

The ``open_sync`` method has been removed from :class:`MotorClient` and
:class:`MotorReplicaSetClient`. Clients now connect to MongoDB automatically on
first use. Simply delete the call to ``open_sync`` from your application.

If it's important to test that MongoDB is available before continuing
your application's startup, use ``IOLoop.run_sync``::

    loop = tornado.ioloop.IOLoop.current()
    client = motor.MotorClient(host, port)
    try:
        loop.run_sync(client.open)
    except pymongo.errors.ConnectionFailure:
        print "Can't connect"

Similarly, calling :meth:`MotorGridOut.open` is now optional.
:class:`MotorGridIn` and :class:`MotorGridFS` no longer have an ``open``
method at all.

.. _changelog-futures:

Futures
'''''''

Motor 0.2 takes advantage of Tornado's tidy new coroutine syntax::

    # Old style:
    document = yield motor.Op(collection.find_one, {'_id': my_id})

    # New style:
    document = yield collection.find_one({'_id': my_id})

To make this possible, Motor asynchronous methods
(except :meth:`MotorCursor.each`) now return a
:class:`~tornado.concurrent.Future`.

Using Motor with callbacks is still possible: If a callback is passed, it will
be executed with the ``(result, error)`` of the operation, same as in Motor
0.1::

    def callback(document, error):
        if error:
            logging.error("Oh no!")
        else:
            print document

    collection.find_one({'_id': my_id}, callback=callback)

If no callback is passed, a Future is returned that resolves to the
method's result or error::

    document = yield collection.find_one({'_id': my_id})

``motor.Op`` works the same as before, but it's deprecated.

``WaitOp`` and ``WaitAllOps`` have been removed. Code that used them can now
yield a ``Future`` or a list of them. Consider this function written for
Tornado 2 and Motor 0.1::

    @gen.engine
    def get_some_documents():
        cursor = collection.find().sort('_id').limit(2)
        cursor.to_list(callback=(yield gen.Callback('key')))
        do_something_while_we_wait()
        try:
            documents = yield motor.WaitOp('key')
            print documents
        except Exception, e:
            print e

The function now becomes::

    @gen.coroutine
    def f():
        cursor = collection.find().sort('_id').limit(2)
        future = cursor.to_list(2)
        do_something_while_we_wait()
        try:
            documents = yield future
            print documents
        except Exception, e:
            print e

Similarly, a function written like so in the old style::

    @gen.engine
    def get_two_documents_in_parallel(collection):
        collection.find_one(
            {'_id': 1}, callback=(yield gen.Callback('one')))

        collection.find_one(
            {'_id': 2}, callback=(yield gen.Callback('two')))

        try:
            doc_one, doc_two = yield motor.WaitAllOps(['one', 'two'])
            print doc_one, doc_two
        except Exception, e:
            print e

Now becomes::

    @gen.coroutine
    def get_two_documents_in_parallel(collection):
        future_0 = collection.find_one({'_id': 1})
        future_1 = collection.find_one({'_id': 2})

        try:
            doc_one, doc_two = yield [future_0, future_1]
            print doc_one, doc_two
        except Exception, e:
            print e


to_list
'''''''

Any calls to :meth:`MotorCursor.to_list` that omitted the ``length``
argument must now include it::

    result = yield collection.find().to_list(100)

``None`` is acceptable, meaning "unlimited." Use with caution.

Connection Pooling
''''''''''''''''''

:class:`MotorPool` has been rewritten. It supports the new options
introduced in PyMongo 2.6, and drops all Motor-specific options.

:class:`MotorClient` and :class:`MotorReplicaSetClient` have an option
``max_pool_size``. It used to mean "minimum idle sockets to keep open", but its
meaning has changed to "maximum sockets open per host." Once this limit is
reached, operations will pause waiting for a socket to become available.
Therefore the default has been raised from 10 to 100. If you pass a value for
``max_pool_size`` make sure it's large enough for the expected load. (Sockets
are only opened when needed, so there's no cost to having a ``max_pool_size``
larger than necessary. Err towards a larger value.) If you've been accepting
the default, continue to do so.

``max_pool_size`` is now synonymous with Motor's special ``max_concurrent``
option, so ``max_concurrent`` has been removed.

``max_wait_time`` has been renamed ``waitQueueTimeoutMS`` for consistency with
PyMongo. If you pass ``max_wait_time``, rename it and multiply by 1000.

The :exc:`MotorPoolTimeout` exception is gone; catch PyMongo's
:exc:`~pymongo.errors.ConnectionFailure` instead.

DNS
'''

Motor can take advantage of Tornado 3's `asynchronous resolver interface`_. By
default, Motor still uses blocking DNS, but you can enable non-blocking
lookup with a threaded resolver::

    Resolver.configure('tornado.netutil.ThreadedResolver')

Or install `pycares`_ and use the c-ares resolver::

    Resolver.configure('tornado.platform.caresresolver.CaresResolver')

MotorCursor.tail
''''''''''''''''

The ``MotorCursor.tail`` method has been removed. It was complex, diverged from
PyMongo's feature set, and encouraged overuse of MongoDB capped collections as
message queues when a purpose-built message queue is more appropriate. An
example of tailing a capped collection is provided instead:
:doc:`examples/tailable-cursors`.

MotorClient.is_locked
'''''''''''''''''''''

``is_locked`` has been removed since calling it from Motor would be
bizarre. If you called ``MotorClient.is_locked`` like::

    locked = yield motor.Op(client.is_locked)

you should now do::

    result = yield client.admin.current_op()
    locked = bool(result.get('fsyncLock', None))

The result is ``True`` only if an administrator has called `fsyncLock`_ on the
mongod. It is unlikely that you have any use for this.

GridFSHandler
'''''''''''''

:meth:`~web.GridFSHandler.get_gridfs_file` now
returns a Future instead of accepting a callback.

.. _Greenlet: http://pypi.python.org/pypi/greenlet/
.. _asynchronous resolver interface: http://www.tornadoweb.org/en/stable/netutil.html#tornado.netutil.Resolver
.. _pycares: https://pypi.python.org/pypi/pycares
.. _fsyncLock: http://docs.mongodb.org/manual/reference/method/db.fsyncLock/

New Features
~~~~~~~~~~~~

The introduction of a :ref:`Futures-based API <changelog-futures>` is the most
pervasive new feature. In addition Motor 0.2 includes new features from
PyMongo 2.6 and 2.7:

* :meth:`MotorCollection.aggregate` can return a cursor.
* Support for all current MongoDB authentication mechanisms (see PyMongo's
  `authentication examples`_).
* A new :meth:`MotorCollection.parallel_scan` method.
* An :doc:`API for bulk writes <examples/bulk>`.
* Support for wire protocol changes in MongoDB 2.6.
* The ability to specify a server-side timeout for operations
  with :meth:`~MotorCursor.max_time_ms`.
* A new :meth:`MotorGridFS.find` method for querying GridFS.

.. _authentication examples: http://api.mongodb.org/python/current/examples/authentication.html

Bugfixes
~~~~~~~~

``MotorReplicaSetClient.open`` threw an error if called without a callback.

``MotorCursor.to_list`` `ignored SON manipulators
<https://jira.mongodb.org/browse/MOTOR-8>`_. (Thanks to Eren Güven for the
report and the fix.)

`The full list is in Jira
<https://jira.mongodb.org/browse/MOTOR-23?filter=15038>`_.

Motor 0.1.2
-----------

Fixes innocuous unittest failures when running against Tornado 3.1.1.

Motor 0.1.1
-----------

Fixes issue `MOTOR-12`_ by pinning its PyMongo dependency to PyMongo version
2.5.0 exactly.

Motor relies on some of PyMongo's internal details, so changes to PyMongo can
break Motor, and a change in PyMongo 2.5.1 did. Eventually PyMongo will expose
stable hooks for Motor to use, but for now I changed Motor's dependency from
``PyMongo>=2.4.2`` to ``PyMongo==2.5.0``.

.. _MOTOR-12: https://jira.mongodb.org/browse/MOTOR-12
