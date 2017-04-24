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

 - ``DB_IP``:         Defaults to "localhost", can be a domain name or IP
 - ``DB_PORT``:       Defaults to 27017
 - ``DB_USER``:       If auth is enabled the test suite creates an admin user by
   default, or logs in to the admin database with the username provided
 - ``DB_PASSWORD``:   If auth is enabled the test suite creates an admin user by
   default, or logs in to the admin database with the username provided
- ``CERT_DIR``:       Path with alternate client.pem and ca.pem for testing.
                      Otherwise the suite uses those in test/certificates/.

Install `tox`_ and run it from the command line in the repository directory.
You will need a variety of Python interpreters installed. For a minimal test,
ensure you have Python 2.7 and 3.5, and run::

  > tox -e tornado4-py27,tornado4-py35

The doctests pass with Python 3.5 and a MongoDB 3.2 instance running on
port 27017:

  > tox -e py3-sphinx-doctest

.. _tox: https://testrun.org/tox/

General Guidelines
------------------

- Avoid backward breaking changes if at all possible.
- Write inline documentation for new classes and methods.
- Add yourself to doc/contributors.rst :)
