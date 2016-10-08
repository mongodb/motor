AIOHTTPGridFS Example
=====================

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
