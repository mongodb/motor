=====
Motor
=====

.. image:: https://raw.github.com/mongodb/motor/master/doc/_static/motor.png

:Info: Motor is a full-featured, non-blocking MongoDB_ driver for Python
    Tornado_ and asyncio_ applications.
:Author: A\. Jesse Jiryu Davis

About
=====

Motor presents a coroutine-based API for non-blocking access
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

* Unix, including macOS. Windows is not supported.
* PyMongo_ 3.10 or later.
* Python 3.5 or later.

See `requirements <https://motor.readthedocs.io/en/stable/requirements.html>`_
for details about compatibility.

How To Ask For Help
===================

Issues with, questions about, or feedback for Motor should be sent to the
`MongoDB Community Forums`_.

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

.. _ReadTheDocs: https://motor.readthedocs.io/

.. _MongoDB Community Forums:
   https://community.mongodb.com/tags/c/drivers-odms-connectors/7/motor-driver

.. _sphinx: http://sphinx.pocoo.org/
