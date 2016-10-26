Requirements
============

The current version of Motor requires:

* CPython 2.6, 2.7, or 3.3 and later.
* PyMongo_ 2.9.x.

Beginning with version 0.5, Motor can integrate with either Tornado or asyncio.

Requires the `futures`_ package from PyPI on Python 2.

The default authentication mechanism for MongoDB 3.0+ is SCRAM-SHA-1.
Install `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
especially on Python older than 2.7.8, or on Python 3.3.

(Python 2.7.9 and later, or Python 3.4 and later, have builtin hash functions
nearly as fast as backports.pbkdf2.)

Building the docs requires `sphinx`_.

In Python 2.6, unittest2_ is automatically installed by
``python setup.py test``.

.. _PyMongo: https://pypi.python.org/pypi/pymongo/

.. _futures: https://pypi.python.org/pypi/futures

.. _backports.pbkdf2: https://pypi.python.org/pypi/backports.pbkdf2/

.. _sphinx: http://sphinx.pocoo.org/

.. _unittest2: https://pypi.python.org/pypi/unittest2


Compatibility Matrix
--------------------

Motor and PyMongo
`````````````````

Older versions of Motor depended on exact PyMongo versions. Starting in 0.7,
Motor can depend on the latest PyMongo 2.9.x release, starting with 2.9.4
and above.

+-------------------+-----------------+
| Motor Version     | PyMongo Version |
+===================+=================+
| 0.1               | 2.5.0           |
+-------------------+-----------------+
| 0.2               | 2.7.0           |
+-------------------+-----------------+
| 0.3               | 2.7.1           |
+-------------------+-----------------+
| 0.4               | 2.8.0           |
+-------------------+-----------------+
| 0.5               | 2.8.0           |
+-------------------+-----------------+
| 0.6               | 2.8.0           |
+-------------------+-----------------+
| 0.7               | 2.9.4+          |
+-------------------+-----------------+

Motor and MongoDB
`````````````````

All Motor versions are usable with all MongoDB versions as old as 2.2.
Where "N" appears there are some incompatibilities and
unsupported server features.

+---------------------------------------------------+
|               MongoDB Version                     |
+=====================+=====+=====+=====+=====+=====+
|                     | 2.2 | 2.4 | 2.6 | 3.0 | 3.2 |
+---------------+-----+-----+-----+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.2 |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.3 |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.4 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.5 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.6 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.7 |  Y  |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+

There is no relationship between PyMongo and MongoDB version numbers, although
the numbers happen to be close in recent releases of PyMongo and MongoDB.
Use `the PyMongo compatibility matrix`_ to determine what MongoDB version is
supported by PyMongo. Use the compatibility matrix above to determine what
MongoDB version Motor supports.

.. _the PyMongo compatibility matrix: https://docs.mongodb.org/ecosystem/drivers/python/#mongodb-compatibility

Motor and Tornado
`````````````````

Where "N" appears in this matrix, the versions of Motor and Tornado are
known to be incompatible, or have not been tested together.

+---------------------------------+
|       Tornado Version           |
+=====================+=====+=====+
|                     | 3.x | 4.x |
+---------------+-----+-----+-----+
| Motor Version | 0.1 |  Y  |**N**|
+---------------+-----+-----+-----+
|               | 0.2 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 0.3 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 0.4 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 0.5 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 0.6 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 0.7 |  Y  |  Y  |
+---------------+-----+-----+-----+

Motor and Python
````````````````

Until version 0.5, Motor required Tornado, and it supported the same version of
Python as its supported Tornado versions did.

Beginning in version 0.5, Motor integrates with asyncio or Tornado.
For asyncio support specifically, Motor requires Python 3.4+, or Python 3.3
with the `asyncio package from PyPI`_.

+----------------------------------------------------------------+
|                   Python Version                               |
+=====================+=====+=====+=====+======+=====+=====+=====+
|                     | 2.5 | 2.6 | 2.7 | 3.3  | 3.4 | 3.5 | 3.6 |
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |  Y  |  Y   |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.2 |**N**|  Y  |  Y  |  Y   |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.3 |**N**|  Y  |  Y  |  Y   |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.4 |**N**|  Y  |  Y  |  Y   |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.5 |**N**|  Y  |  Y  |  Y   |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.6 |**N**|  Y  |  Y  |  Y   |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+------+-----+-----+-----+
|               | 0.7 |**N**|  Y  |  Y  |  Y   |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+------+-----+-----+-----+

.. _asyncio package from PyPI: https://pypi.python.org/pypi/asyncio

Not Supported
-------------

Motor does not support Jython or Windows.
