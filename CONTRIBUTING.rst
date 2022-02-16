Contributing to Motor
=====================

Contributions are encouraged. Please read these guidelines before sending a
pull request.

Bugfixes and New Features
-------------------------

Before starting to write code, look for existing tickets or create one in `Jira
<https://jira.mongodb.org/browse/MOTOR>`_ for your specific issue or feature
request.

Running Tests
-------------

Install a recent version of MongoDB and run it on the default port from a clean
data directory. Pass "--setParameter enableTestCommands=1" to mongod to enable
testing MotorCursor's ``max_time_ms`` method.

Control how the tests connect to MongoDB with these environment variables:

 - ``DB_IP``: Defaults to "localhost", can be a domain name or IP
 - ``DB_PORT``: Defaults to 27017
 - ``DB_USER``, ``DB_PASSWORD``: To test with authentication, create an admin
   user and set these environment variables to the username and password
 - ``CERT_DIR``: Path with alternate client.pem and ca.pem for testing.
   Otherwise the suite uses those in test/certificates/.

Install `tox`_ and run it from the command line in the repository directory.
You will need a variety of Python interpreters installed. For a minimal test,
ensure you have Python 3.9, and run::

  > tox -e asyncio-py39

The doctests pass with Python 3.7 and a MongoDB 5.0 instance running on
port 27017:

  > tox -e py3-sphinx-doctest

.. _tox: https://testrun.org/tox/

Running Linters
---------------

Motor uses `pre-commit <https://pypi.org/project/pre-commit/>`_
for managing linting of the codebase.
``pre-commit`` performs various checks on all files in Motor and uses tools
that help follow a consistent code style within the codebase.

To set up ``pre-commit`` locally, run::

    pip install pre-commit
    pre-commit install

To run ``pre-commit`` manually, run::

    > tox -e lint

General Guidelines
------------------

- Avoid backward breaking changes if at all possible.
- Write inline documentation for new classes and methods.
- Add yourself to doc/contributors.rst :)
