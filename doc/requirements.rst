Requirements
============

The current version of Motor requires:

* CPython 2.6, 2.7, 3.3, or 3.4.
* PyMongo_ 2.8.0 exactly.
* Tornado_ 3.1 or later.
* Greenlet_

The default authentication mechanism for MongoDB 3.0+ is SCRAM-SHA-1.
Install `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
especially on Python older than 2.7.8, or on Python 3 before Python 3.4.

Building the docs requires `sphinx`_.

In Python 2.6, unittest2_ is automatically installed by
``python setup.py test``.

.. _PyMongo: https://pypi.python.org/pypi/pymongo/

.. _Tornado: http://www.tornadoweb.org

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

Motor and MongoDB
`````````````````

All Motor versions are usable with MongoDB versions as old as 2.2.
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

Motor and Tornado
`````````````````

Where "N" appears in this matrix, the versions of Motor and Tornado are
completely incompatible.

+---------------------------------------------------+
|                     Tornado Version               |
+=====================+=====+=====+=====+=====+=====+
|                     | 2.4 | 3.0 | 3.1 | 3.2 | 4.0 |
+---------------+-----+-----+-----+-----+-----+-----+
| Motor Version | 0.1 |  Y  |  Y  |  Y  |  Y  |**N**|
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.2 |**N**|**N**|  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.3 |**N**|**N**|  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+
|               | 0.4 |**N**|**N**|  Y  |  Y  |  Y  |
+---------------+-----+-----+-----+-----+-----+-----+

Motor and Python
````````````````

Motor requires Tornado, and it supports the same version of Python as its
supported Tornado versions do.

Beginning in version 0.5, Motor will integrate with asyncio or Tornado.
asyncio support will require Python 3.4.

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


Not Supported
-------------

Code that executes greenlets has performed very poorly on PyPy until recently.
I must reevaluate whether PyPy is supported or not.

Motor does not support Jython or Windows.
