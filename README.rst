=====
Motor
=====

.. image:: https://raw.github.com/mongodb/motor/master/doc/_static/motor.png

:Info: Motor is a full-featured, non-blocking MongoDB_ driver for Python
    Tornado_ and asyncio_ applications.
:Documentation: Available at `motor.readthedocs.io <https://motor.readthedocs.io/en/stable/>`_
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

Support / Feedback
==================

For issues with, questions about, or feedback for PyMongo, please look into
our `support channels <https://support.mongodb.com/welcome>`_. Please
do not email any of the Motor developers directly with issues or
questions - you're more likely to get an answer on the `MongoDB Community
Forums <https://developer.mongodb.com/community/forums/tag/motor-driver>`_.

Bugs / Feature Requests
=======================

Think you've found a bug? Want to see a new feature in Motor? Please open a
case in our issue management tool, JIRA:

- `Create an account and login <https://jira.mongodb.org>`_.
- Navigate to `the MOTOR project <https://jira.mongodb.org/browse/MOTOR>`_.
- Click **Create Issue** - Please provide as much information as possible about the issue type and how to reproduce it.

Bug reports in JIRA for all driver projects (i.e. MOTOR, CSHARP, JAVA) and the
Core Server (i.e. SERVER) project are **public**.

How To Ask For Help
-------------------

Please include all of the following information when opening an issue:

- Detailed steps to reproduce the problem, including full traceback, if possible.
- The exact python version used, with patch level::

  $ python -c "import sys; print(sys.version)"

- The exact version of Motor used, with patch level::

  $ python -c "import motor; print(motor.version)"

- The exact version of PyMongo used, with patch level::

  $ python -c "import pymongo; print(pymongo.version); print(pymongo.has_c())"

- The exact Tornado version, if you are using Tornado::

  $ python -c "import tornado; print(tornado.version)"

- The operating system and version (e.g. RedHat Enterprise Linux 6.4, OSX 10.9.5, ...)

Security Vulnerabilities
------------------------

If you've identified a security vulnerability in a driver or any other
MongoDB project, please report it according to the `instructions here
<http://docs.mongodb.org/manual/tutorial/create-a-vulnerability-report>`_.

Installation
============

Motor can be installed with `pip <http://pypi.python.org/pypi/pip>`_::

  $ pip install motor

Dependencies
============

Motor works in all the environments officially supported by Tornado or by
asyncio. It requires:

* Unix (including macOS) or Windows.
* PyMongo_ >=3.11,<4
* Python 3.5+

See `requirements <https://motor.readthedocs.io/en/stable/requirements.html>`_
for details about compatibility.

Examples
========

See the `examples on ReadTheDocs <https://motor.readthedocs.io/en/stable/examples/index.html>`_.

Documentation
=============

Motor's documentation is on ReadTheDocs_.

Build the documentation with Python 3.5. Install sphinx_, Tornado_, and aiohttp_,
and do ``cd doc; make html``.

Testing
=======

Run ``python setup.py test``.
Tests are located in the ``test/`` directory.

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

.. _MongoDB: http://mongodb.org/

.. _Tornado: http://tornadoweb.org/

.. _asyncio: https://docs.python.org/3/library/asyncio.html

.. _aiohttp: https://github.com/aio-libs/aiohttp

.. _ReadTheDocs: https://motor.readthedocs.io/en/stable/

.. _sphinx: http://sphinx.pocoo.org/
