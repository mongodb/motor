==============
Motor Features
==============

Non-Blocking
============
Motor is an asynchronous driver for MongoDB and Tornado_.
Motor never blocks Tornado's IOLoop while connecting to MongoDB or
performing I/O.

.. _Tornado: http://tornadoweb.org/

Featureful
==========
Motor wraps almost all of PyMongo's API and makes it non-blocking. For the few
PyMongo features not implemented in Motor, see :doc:`differences`.

Convenient With `tornado.gen`
=============================
The :mod:`tornado.gen` module lets you use coroutines to simplify asynchronous
code. Motor methods return Futures that are convenient to use with coroutines.
See :ref:`the coroutine example <coroutine-example>`.

Timeouts
========
Unlike most non-blocking libraries for Tornado, Motor provides a convenient
timeout interface::

    @gen.coroutine
    def f():
        try:
            document = yield db.collection.find_one(my_complex_query, network_timeout=5)
        except pymongo.errors.ConnectionFailure:
            # find_one took more than 5 seconds
            pass

Configurable IOLoops
====================
Motor supports Tornado applications with multiple
:class:`IOLoops <tornado.ioloop.IOLoop>`. Pass the ``io_loop``
argument to :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient` to configure the loop for a
client instance.

Streams Static Files from GridFS
================================
Motor can stream data from `GridFS <http://dochub.mongodb.org/core/gridfs>`_
to a Tornado :class:`~tornado.web.RequestHandler`
using :meth:`~motor.MotorGridOut.stream_to_handler` or
the :class:`~motor.web.GridFSHandler` class.
