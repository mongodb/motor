asyncio GridFS Classes
======================

.. warning:: As of May 14th, 2025, Motor is deprecated in favor of the GA release of the PyMongo Async API.
  No new features will be added to Motor, and only bug fixes will be provided until it reaches end of life on May 14th, 2026.
  After that, only critical bug fixes will be made until final support ends on May 14th, 2027.
  We strongly recommend migrating to the PyMongo Async API while Motor is still supported.
  For help transitioning, see the `Migrate to PyMongo Async guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. currentmodule:: motor.motor_asyncio

Store blobs of data in `GridFS <http://dochub.mongodb.org/core/gridfs>`_.

.. seealso:: :ref:`Differences between PyMongo's and Motor's GridFS APIs
  <gridfs-differences>`.

.. autoclass:: AsyncIOMotorGridFSBucket
  :members:

.. autoclass:: AsyncIOMotorGridIn
  :members:

.. autoclass:: AsyncIOMotorGridOut
  :members:

.. autoclass:: AsyncIOMotorGridOutCursor
  :members:
