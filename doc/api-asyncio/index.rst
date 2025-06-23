Motor asyncio API
=================

.. warning:: As of May 14th, 2025, Motor is deprecated in favor of the GA release of the PyMongo Async API.
  No new features will be added to Motor, and only bug fixes will be provided until it reaches end of life on May 14th, 2026.
  After that, only critical bug fixes will be made until final support ends on May 14th, 2027.
  We strongly recommend migrating to the PyMongo Async API while Motor is still supported.
  For help transitioning, see the `Migrate to PyMongo Async guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.

.. toctree::

    asyncio_motor_client
    asyncio_motor_client_session
    asyncio_motor_database
    asyncio_motor_collection
    asyncio_motor_change_stream
    asyncio_motor_client_encryption
    cursors
    asyncio_gridfs
    aiohttp

.. seealso:: :doc:`../tutorial-asyncio`

This page describes using Motor with asyncio. For Tornado integration, see
:doc:`../api-tornado/index`.
