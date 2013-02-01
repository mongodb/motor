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
The `tornado.gen module`_ lets you use generators to simplify asynchronous code,
combining operations and their callbacks in a single function. Motor provides
yield points to be used with ``tornado.gen``.
See :doc:`api/generator_interface`.

.. _tornado.gen module: http://www.tornadoweb.org/documentation/gen.html

Timeouts
========
Unlike most non-blocking libraries for Tornado, Motor provides a convenient
timeout interface::

    @gen.engine
    def f():
        try:
            document = yield motor.Op(
                db.collection.find_one, my_complex_query, network_timeout=5)
        except pymongo.errors.ConnectionFailure:
            # find_one took more than 5 seconds
            pass

Bounded Connection Growth
=========================
Motor has a default cap of 100 connections per host
per :class:`~motor.MotorClient` or :class:`~motor.MotorReplicaSetClient`,
configurable with the ``max_concurrent`` option. Operations yield to the
event loop while waiting for a spare connection to use.

Configurable IOLoops
====================
Motor supports Tornado applications with multiple IOLoops_. Pass the ``io_loop``
argument to :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient` to configure the loop for a
client instance.

.. _IOLoops: http://www.tornadoweb.org/documentation/ioloop.html

Opens Connections Synchronously or Asynchronously
=================================================
A :class:`~motor.MotorClient` or :class:`~motor.MotorReplicaSetClient`
can be opened synchronously with :meth:`~motor.MotorClient.open_sync`
before your application begins serving request, or can be opened
asynchronously with :meth:`~motor.MotorClient.open` to make the connection
to MongoDB without blocking the Tornado IOLoop.

Streams Static Files from GridFS
================================
Motor can stream data from GridFS_ to a Tornado RequestHandler_
using :meth:`~motor.MotorGridOut.stream_to_handler` or
the :class:`~motor.web.GridFSHandler` class.

.. _GridFS: http://www.mongodb.org/display/DOCS/GridFS

.. _RequestHandler: http://www.tornadoweb.org/documentation/web.html#request-handlers

Tailable Cursors
================
MotorCursor provides a convenient :meth:`~motor.MotorCursor.tail` method to
watch a MongoDB capped collection and execute a callback with each new document
as it is inserted.
