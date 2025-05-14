AIOHTTPGridFS Example
=====================

.. warning:: Motor will be deprecated on May 14th, 2026, one year after the production release of the PyMongo Async driver. Critical bug fixes will be made until May 14th, 2027.
  We strongly recommend that Motor users migrate to the PyMongo Async driver while Motor is still supported.
  To learn more, see `the migration guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.


Serve pre-compressed static content from GridFS over HTTP. Uses the `aiohttp`_
web framework and :class:`~motor.aiohttp.AIOHTTPGridFS`.

.. _aiohttp: https://aiohttp.readthedocs.io/

Instructions
------------

Start a MongoDB server on its default port and run this script. Then visit:

http://localhost:8080/fs/my_file

Serve compressed static content from GridFS
-------------------------------------------

.. literalinclude:: aiohttp_gridfs_example.py
  :language: python3
  :start-after: include-start
