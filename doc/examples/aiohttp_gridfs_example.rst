AIOHTTPGridFS Example
=====================

.. warning:: As of May 14th, 2025, Motor is deprecated in favor of the GA release of the PyMongo Async API.
  No new features will be added to Motor, and only bug fixes will be provided until it reaches end of life on May 14th, 2026.
  After that, only critical bug fixes will be made until final support ends on May 14th, 2027.
  We strongly recommend migrating to the PyMongo Async API while Motor is still supported.
  For help transitioning, see the `Migrate to PyMongo Async guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.


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
