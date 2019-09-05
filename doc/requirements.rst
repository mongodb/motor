Requirements
============

The current version of Motor requires:

* CPython 2.7, or 3.4 and later.
* PyMongo_ 3.9 and later.

Motor can integrate with either Tornado or asyncio.

Requires the `futures`_ package from PyPI on Python 2.

The default authentication mechanism for MongoDB 3.0+ is SCRAM-SHA-1.
Install `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
especially on Python older than 2.7.8.

(Python 2.7.9 and later, or Python 3.4 and later, have builtin hash functions
nearly as fast as backports.pbkdf2.)

Building the docs requires `sphinx`_.

.. _PyMongo: https://pypi.python.org/pypi/pymongo/

.. _futures: https://pypi.python.org/pypi/futures

.. _backports.pbkdf2: https://pypi.python.org/pypi/backports.pbkdf2/

.. _sphinx: http://sphinx.pocoo.org/

Starting in version 2.1, Motor offers experimental support for Windows when it
is using the asyncio event loop. This means it supports Windows exclusively
with Python 3, either integrating with asyncio directly or with Tornado 5 or
later: starting in version 5, Tornado uses the asyncio event loop on Python 3
by default.

.. _compatibility-matrix:

Compatibility Matrix
--------------------

Motor and PyMongo
`````````````````

+-------------------+-----------------+
| Motor Version     | PyMongo Version |
+===================+=================+
| 1.0               | 3.3+            |
+-------------------+-----------------+
| 1.1               | 3.4+            |
+-------------------+-----------------+
| 1.2               | 3.6+            |
+-------------------+-----------------+
| 1.3               | 3.6+            |
+-------------------+-----------------+
| 2.0               | 3.7+            |
+-------------------+-----------------+
| 2.1               | 3.9+            |
+-------------------+-----------------+

Motor and MongoDB
`````````````````

+---------------------------------------------------------------------------+
|                    MongoDB Version                                        |
+=====================+=====+=====+=====+=====+=====+=====+=====+=====+=====+
|                     | 2.2 | 2.4 | 2.6 | 3.0 | 3.2 | 3.4 | 3.6 | 4.0 | 4.2 |
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
| Motor Version | 1.0 |  Y  |  Y  |  Y  |  Y  |  Y  |**N**|**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
|               | 1.1 |  Y  |  Y  |  Y  |  Y  |  Y  |  Y  |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
|               | 1.2 |**N**|**N**|  Y  |  Y  |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
|               | 1.3 |**N**|**N**|  Y  |  Y  |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
|               | 2.0 |**N**|**N**|**N**|  Y  |  Y  |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+
|               | 2.1 |**N**|**N**|**N**|  Y  |  Y  |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-----+-----+-----+-----+

There is no relationship between PyMongo and MongoDB version numbers, although
the numbers happen to be close or equal in recent releases of PyMongo and MongoDB.
Use `the PyMongo compatibility matrix`_ to determine what MongoDB version is
supported by PyMongo. Use the compatibility matrix above to determine what
MongoDB version Motor supports.

.. _the PyMongo compatibility matrix: https://docs.mongodb.org/ecosystem/drivers/python/#mongodb-compatibility

Motor and Tornado
`````````````````

Where "N" appears in this matrix, the versions of Motor and Tornado are
known to be incompatible, or have not been tested together.

+---------------------------------------------+
|       Tornado Version                       |
+=====================+=====+=====+=====+=====+
|                     | 3.x | 4.x | 5.x | 6.x |
+---------------+-----+-----+-----+-----+-----+
| Motor Version | 1.0 |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 1.1 |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 1.2 |**N**|  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 1.3 |**N**|  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 2.0 |**N**|  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 2.1 |**N**|  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+

Motor and Python
````````````````

Motor 1.2 dropped support for the short-lived version of
the "async for" protocol implemented in Python 3.5.0 and 3.5.1. Motor continues
to work with "async for" loops in Python 3.5.2 and later.

Motor 1.2.5 and 1.3.1 add compatibility with Python 3.7, but at the cost of
dropping Python 3.4.3 and older. Python 3.4.4 and later are supported by all
Motor versions.

+-------------------------------------------------------------------------------+
|                   Python Version                                              |
+=====================+=====+=====+=====+=====+=====+=======+=======+=====+=====+
|                     | 2.5 | 2.6 | 2.7 | 3.3 | 3.4 | 3.5.0 | 3.5.2 | 3.6 | 3.7 |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
| Motor Version | 1.0 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
|               | 1.1 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
|               | 1.2 |**N**|**N**|  Y  |**N**|  Y  |**N**  |  Y    |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
|               | 1.3 |**N**|**N**|  Y  |**N**|  Y  |**N**  |  Y    |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
|               | 2.0 |**N**|**N**|  Y  |**N**|  Y  |**N**  |  Y    |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+
|               | 2.1 |**N**|**N**|  Y  |**N**|  Y  |**N**  |  Y    |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+-----+

Not Supported
-------------

Motor does not support Jython or IronPython.
