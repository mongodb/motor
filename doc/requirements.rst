Requirements
============

The current version of Motor requires:

* CPython 2.6, 2.7, or 3.3 and later.
* PyMongo_ 2.8.0 exactly.
* Greenlet_

Beginning with version 0.5, Motor can integrate with either Tornado or asyncio.

The default authentication mechanism for MongoDB 3.0+ is SCRAM-SHA-1.
Install `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
especially on Python older than 2.7.8, or on Python 3.3.

(Python 2.7.9 and later, or Python 3.4 and later, have builtin hash functions
nearly as fast as backports.pbkdf2.)

Building the docs requires `sphinx`_.

In Python 2.6, unittest2_ is automatically installed by
``python setup.py test``.

.. _PyMongo: https://pypi.python.org/pypi/pymongo/

.. _Greenlet: http://pypi.python.org/pypi/greenlet/

.. _backports.pbkdf2: https://pypi.python.org/pypi/backports.pbkdf2/

.. _sphinx: http://sphinx.pocoo.org/

.. _unittest2: https://pypi.python.org/pypi/unittest2


Compatibility Matrix
--------------------

Motor and PyMongo
`````````````````

Motor wraps PyMongo and depends on it intimately. You must use the exact
PyMongo version specified for each version of Motor.

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

Motor and MongoDB
`````````````````

All Motor versions are usable with all MongoDB versions as old as 2.2.
Where "N" appears there are some incompatibilities and
unsupported server features.

+---------------------------------------------+
|               MongoDB Version               |
+=====================+=====+=====+=====+=====+
|                     | 2.2 | 2.4 | 2.6 | 3.0 |
+---------------+-----+-----+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 0.2 |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 0.3 |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+
|               | 0.4 |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+
|               | 0.5 |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+

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

+---------------------------------------------------+
|                 Tornado Version                   |
+=====================+=====+=====+=====+=====+=====+
|                     | 3.1 | 3.2 | 4.0 | 4.1 | 4.2 |
+---------------+-----+-----+-----+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.2 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.3 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.4 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.5 |  Y  |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+

Motor and Python
````````````````

Until version 0.5, Motor required Tornado, and it supported the same version of
Python as its supported Tornado versions did.

Beginning in version 0.5, Motor integrates with asyncio or Tornado.
For asyncio support specifically, Motor requires Python 3.4+, or Python 3.3
with the `asyncio package from PyPI`_.

+-----------------------------------------------------------------------------+
|                   Python Version                                            |
+=====================+=====+=====+=====+==================+==================+
|                     | 2.5 | 2.6 | 2.7 | 3.3 (Sept. 2012) | 3.4 (March 2014) |
+---------------+-----+-----+-----+-----+------------------+------------------+
| Motor Version | 0.1 |  Y  |  Y  |  Y  |  Y               |**N**             |
+---------------+-----+-----+-----+-----+------------------+------------------+
|               | 0.2 |**N**|  Y  |  Y  |  Y               |**N**             |
+---------------+-----+-----+-----+-----+------------------+------------------+
|               | 0.3 |**N**|  Y  |  Y  |  Y               |  Y               |
+---------------+-----+-----+-----+-----+------------------+------------------+
|               | 0.4 |**N**|  Y  |  Y  |  Y               |  Y               |
+---------------+-----+-----+-----+-----+------------------+------------------+
|               | 0.5 |**N**|  Y  |  Y  |  Y               |  Y               |
+---------------+-----+-----+-----+-----+------------------+------------------+

.. _asyncio package from PyPI: https://pypi.python.org/pypi/asyncio

Not Supported
-------------

Code that executes greenlets has performed very poorly on PyPy in the past.
I must reevaluate whether PyPy is supported or not.

Motor does not support Jython or Windows.
