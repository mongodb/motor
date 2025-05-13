==============
Motor Features
==============

.. currentmodule:: motor.motor_tornado

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.


Non-Blocking
============
Motor is an asynchronous driver for MongoDB. It can be used from Tornado_ or
asyncio_ applications.
Motor never blocks the event loop while connecting to MongoDB or
performing I/O.

.. _Tornado: http://tornadoweb.org/

.. _asyncio: https://docs.python.org/3/library/asyncio.html

Featureful
==========
Motor wraps almost all of PyMongo's API and makes it non-blocking. For the few
PyMongo features not implemented in Motor, see :doc:`differences`.

Convenient With ``tornado.gen``
===============================
The :mod:`tornado.gen` module lets you use coroutines to simplify asynchronous
code. Motor methods return Futures that are convenient to use with coroutines.

Configurable IOLoops
====================
Motor supports Tornado applications with multiple
:class:`IOLoops <tornado.ioloop.IOLoop>`. Pass the ``io_loop``
argument to :class:`MotorClient` to configure the loop for a
client instance.

Streams Static Files from GridFS
================================
Motor can stream data from `GridFS <http://dochub.mongodb.org/core/gridfs>`_
to a Tornado :class:`~tornado.web.RequestHandler`
using :meth:`~MotorGridOut.stream_to_handler` or the :class:`~motor.web.GridFSHandler` class.
It can also serve GridFS data with aiohttp using the :class:`~motor.aiohttp.AIOHTTPGridFS` class.
