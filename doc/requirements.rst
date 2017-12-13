Requirements
============

The current version of Motor requires:

* CPython 2.7, or 3.4 and later.
* PyMongo_ 3.6 and later.

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


.. _compatibility-matrix:

Compatibility Matrix
--------------------

Motor and PyMongo
`````````````````

Older versions of Motor depended on exact PyMongo versions. Version 0.7 requires
the latest PyMongo 2.9.x release beginning with 2.9.4, Version 1.0 works
with any PyMongo version beginning with 3.3.0, and Version 1.1 works with any
PyMongo version beginning with 3.4.0.

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
| 1.0               | 3.3+            |
+-------------------+-----------------+
| 1.1               | 3.4+            |
+-------------------+-----------------+
| 1.2               | 3.6+            |
+-------------------+-----------------+

Motor and MongoDB
`````````````````

All Motor versions are usable with all MongoDB versions as old as 2.2.
Where "N" appears there are some incompatibilities and
unsupported server features.

+---------------------------------------------------------+
|               MongoDB Version                           |
+=====================+=====+=====+=====+=====+=====+=====+
|                     | 2.2 | 2.4 | 2.6 | 3.0 | 3.2 | 3.4 |
+---------------+-----+-----+-----+-----+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |**N**|**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.2 |  Y  |  Y  |  Y  |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.3 |  Y  |  Y  |  Y  |**N**|**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.4 |  Y  |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.5 |  Y  |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.6 |  Y  |  Y  |  Y  |  Y  |**N**|**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 0.7 |  Y  |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 1.0 |  Y  |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 1.1 |  Y  |  Y  |  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-----+
|               | 1.2 |**N**|**N**|  Y  |  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-----+

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
|               | 1.0 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 1.1 |  Y  |  Y  |
+---------------+-----+-----+-----+
|               | 1.2 |**N**|  Y  |
+---------------+-----+-----+-----+

Motor and Python
````````````````

Until version 0.5, Motor required Tornado, and it supported the same version of
Python as its supported Tornado versions did.

Beginning in version 0.5, Motor integrates with asyncio or Tornado.

Beginning in version 0.5, supports the "async for" syntax with cursors in
Python 3.5 and later. Motor 1.2 dropped support for the short-lived version of
the "async for" protocol implemented in Python 3.5.0 and 3.5.1. Motor continues
to work with "async for" loops in Python 3.5.2 and later.

+-------------------------------------------------------------------------+
|                   Python Version                                        |
+=====================+=====+=====+=====+=====+=====+=======+=======+=====+
|                     | 2.5 | 2.6 | 2.7 | 3.3 | 3.4 | 3.5.0 | 3.5.2 | 3.6 |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
| Motor Version | 0.1 |  Y  |  Y  |  Y  |  Y  |**N**|**N**  |**N**  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.2 |**N**|  Y  |  Y  |  Y  |**N**|**N**  |**N**  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.3 |**N**|  Y  |  Y  |  Y  |  Y  |**N**  |**N**  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.4 |**N**|  Y  |  Y  |  Y  |  Y  |**N**  |**N**  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.5 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.6 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 0.7 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |**N**|
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 1.0 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 1.1 |**N**|  Y  |  Y  |  Y  |  Y  |  Y    |  Y    |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+
|               | 1.2 |**N**|**N**|  Y  |**N**|  Y  |**N**  |  Y    |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+-------+-------+-----+

.. _asyncio package from PyPI: https://pypi.python.org/pypi/asyncio

Not Supported
-------------

Motor does not support Windows:

* The author does not test Motor on Windows to ensure it is correct or fast.
* Tornado `is not officially supported on Windows
  <http://www.tornadoweb.org/en/stable/index.html#installation>`_,
  so Motor's Tornado integration on Windows is doubly-unsupported.
* Since asyncio *does* officially support Windows, Motor's asyncio integration
  is more likely to work there, but it is untested.

Motor also does not support Jython.
