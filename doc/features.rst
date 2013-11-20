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
The `tornado.gen module`_ lets you use coroutines to simplify asynchronous
code. Motor methods return Futures that are convenient to use with coroutines.
See :ref:`coroutine-example`.

.. _tornado.gen module: http://tornadoweb.org/en/stable/gen.html

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
Motor supports Tornado applications with multiple IOLoops_. Pass the ``io_loop``
argument to :class:`~motor.MotorClient`
or :class:`~motor.MotorReplicaSetClient` to configure the loop for a
client instance.

.. _IOLoops: http://tornadoweb.org/en/stable/ioloop.html

Streams Static Files from GridFS
================================
Motor can stream data from GridFS_ to a Tornado RequestHandler_
using :meth:`~motor.MotorGridOut.stream_to_handler` or
the :class:`~motor.web.GridFSHandler` class.

.. _GridFS: http://docs.mongodb.org/manual/applications/gridfs/

.. _RequestHandler: http://tornadoweb.org/en/stable/web.html#request-handlers
