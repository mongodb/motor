=====
Motor
=====

.. image:: https://raw.github.com/mongodb/motor/master/doc/_static/motor.png

:Info: Motor is a full-featured, non-blocking MongoDB_ driver for Python
    Tornado_ and asyncio_ applications.
:Author: A\. Jesse Jiryu Davis

About
=====

Motor presents a callback- or Future-based API for non-blocking access
to MongoDB. The source is `on GitHub <https://github.com/mongodb/motor>`_
and the docs are on ReadTheDocs_.

    "We use Motor in high throughput environments, processing tens of thousands
    of requests per second. It allows us to take full advantage of modern
    hardware, ensuring we utilise the entire capacity of our purchased CPUs.
    This helps us be more efficient with computing power, compute spend and
    minimises the environmental impact of our infrastructure as a result."

    --*David Mytton, Server Density*

    "We develop easy-to-use sensors and sensor systems with open source
    software to ensure every innovator, from school child to laboratory
    researcher, has the same opportunity to create. We integrate Motor into our
    software to guarantee massively scalable sensor systems for everyone."

    --*Ryan Smith, inXus Interactive*

Installation
============

  $ pip install motor

Dependencies
============

Motor works in all the environments officially supported by Tornado or by
asyncio. It requires:

* Unix, including Mac OS X. Windows is not supported.
* PyMongo_ 3.4 or later.
* Python 2.7 or later.
* `futures`_ on Python 2.7.
* `backports.pbkdf2`_ for faster authentication with MongoDB 3.0+,
  especially on Python older than 2.7.8, or on Python 3 before Python 3.4.

See `requirements <https://motor.readthedocs.io/en/stable/requirements.html>`_
for details about compatibility.

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

- The exact version of PyMongo used::

  $ python -c "import pymongo; print(pymongo.version); print(pymongo.has_c())"

- The exact Tornado version, if you are using Tornado::

  $ python -c "import tornado; print(tornado.version)"

- The operating system and version (e.g. RedHat Enterprise Linux 6.4, OSX 10.9.5, ...)

Documentation
=============

Motor's documentation is on ReadTheDocs_.

Build the documentation with Python 3.5. Install sphinx, Tornado, and aiohttp,
and do ``cd doc; make html``.

Examples
========

See the `examples on ReadTheDocs <https://motor.readthedocs.io/en/latest/examples/index.html>`_.

Testing
=======

Run ``python setup.py test``.
Tests are located in the ``test/`` directory.

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

.. _MongoDB: http://mongodb.org/

.. _Tornado: http://tornadoweb.org/

.. _asyncio: https://docs.python.org/3/library/asyncio.html

.. _futures: https://pypi.python.org/pypi/futures

.. _backports.pbkdf2: https://pypi.python.org/pypi/backports.pbkdf2/

.. _ReadTheDocs: https://motor.readthedocs.io/

.. _mongodb-user list on Google Groups:
   https://groups.google.com/forum/?fromgroups#!forum/mongodb-user

.. _sphinx: http://sphinx.pocoo.org/
