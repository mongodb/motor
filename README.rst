=====
Motor
=====

.. image:: https://raw.github.com/mongodb/motor/master/doc/_static/motor.png

:Info: Motor is a full-featured, non-blocking MongoDB_ driver for Python
    Tornado_ applications.
:Author: A\. Jesse Jiryu Davis

About
=====

Motor presents a Tornado_callback- or Future-based API for non-blocking access
to MongoDB. The source is `on GitHub <https://github.com/mongodb/motor>`_
and the docs are on ReadTheDocs_.

    "Motor uses a clever greenlet-based approach to fully support both
    synchronous and asynchronous interfaces from a single codebase. It's great
    to see companies like MongoDB produce first-party asynchronous drivers for
    their products."

    --*Ben Darnell, Tornado maintainer*

Installation
============

  $ pip install motor

Dependencies
============

Motor works in all the environments officially supported by Tornado_. It
requires:

* Unix, including Mac OS X. Windows is not supported.
* PyMongo_
* Tornado_
* Greenlet_
* Python 2.6 or later.
* `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
  especially on Python older than 2.7.8, or on Python 3 before Python 3.4.

See "Requirements" for details about compatibility.

How To Ask For Help
===================

Issues with, questions about, or feedback for Motor should be sent to the
`mongodb-user list on Google Groups`_.

For confirmed issues or feature requests,
open a case in `Jira <http://jira.mongodb.org>`_ in the "MOTOR" project.
Please include all of the following information:

- Detailed steps to reproduce the problem, including your code and a full
  traceback, if possible.
- What you expected to happen, and what actually happened.
- The exact python version used, with patch level::

  $ python -c "import sys; print(sys.version)"

- The exact version of PyMongo used, with patch level::

  $ python -c "import pymongo; print(pymongo.version); print(pymongo.has_c())"

- The exact Tornado version::

  $ python -c "import tornado; print(tornado.version)"

- The operating system and version (e.g. RedHat Enterprise Linux 6.4, OSX 10.9.5, ...)

Documentation
=============

Motor's documentation is on ReadTheDocs_.

To build the documentation, install sphinx_ and do ``cd doc; make html``.

Examples
========

See the `examples on ReadTheDocs <https://motor.readthedocs.org/en/latest/examples/index.html>`_.

Testing
=======

Run ``python setup.py test``.
Tests are located in the ``test/`` directory.
In Python 2.6, unittest2_ is automatically installed.

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

.. _MongoDB: http://mongodb.org/

.. _Tornado: http://tornadoweb.org/

.. _Greenlet: http://pypi.python.org/pypi/greenlet/

.. _backports.pbkdf2: https://pypi.python.org/pypi/backports.pbkdf2/

.. _ReadTheDocs: http://motor.readthedocs.org/

.. _mongodb-user list on Google Groups:
   https://groups.google.com/forum/?fromgroups#!forum/mongodb-user

.. _sphinx: http://sphinx.pocoo.org/

.. _unittest2: https://pypi.python.org/pypi/unittest2
