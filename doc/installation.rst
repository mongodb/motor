Installation
============

.. warning:: As of May 14th, 2025, Motor is deprecated in favor of the GA release of the PyMongo Async API.
  No new features will be added to Motor, and only bug fixes will be provided until it reaches end of life on May 14th, 2026.
  After that, only critical bug fixes will be made until final support ends on May 14th, 2027.
  We strongly recommend migrating to the PyMongo Async API while Motor is still supported.
  For help transitioning, see the `Migrate to PyMongo Async guide <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/>`_.


Install Motor from PyPI_ with pip_::

  $ python3 -m pip install motor

Pip automatically installs Motor's prerequisite packages.
See :doc:`requirements`.

To install Motor from sources, you can clone its git repository and do::

  $ python3 -m pip install .

Dependencies
------------

Motor works in all the environments officially supported by Tornado or by
asyncio. It requires:

* Unix (including macOS) or Windows.
* PyMongo_ >=4.9,<5
* Python 3.10+

Optional dependencies:

Motor supports same optional dependencies as PyMongo. Required dependencies can be installed
along with Motor.

GSSAPI authentication requires ``gssapi`` extra dependency. The correct
dependency can be installed automatically along with Motor::

  $ pip install "motor[gssapi]"

similarly,

`MONGODB-AWS <https://www.mongodb.com/docs/languages/python/pymongo-driver/current/security/authentication/aws-iam/#std-label-pymongo-mongodb-aws>`_
authentication requires ``aws`` extra dependency::

  $ pip install "motor[aws]"

Support for mongodb+srv:// URIs requires ``srv`` extra dependency::

  $ pip install "motor[srv]"

`OCSP <https://pymongo.readthedocs.io/en/stable/examples/tls.html#ocsp>`_ requires ``ocsp`` extra dependency::

  $ pip install "motor[ocsp]"

Wire protocol compression with snappy requires ``snappy`` extra dependency::

  $ pip install "motor[snappy]"

Wire protocol compression with zstandard requires ``zstd`` extra dependency::

  $ pip install "motor[zstd]"

`Client-Side Field Level Encryption
<https://pymongo.readthedocs.io/en/stable/examples/encryption.html#client-side-field-level-encryption>`_
requires ``encryption`` extra dependency::

  $ pip install "motor[encryption]"

You can install all dependencies automatically with the following
command::

  $ pip install "motor[gssapi,aws,ocsp,snappy,srv,zstd,encryption]"

See `requirements <https://motor.readthedocs.io/en/stable/requirements.html>`_
for details about compatibility.


.. _PyPI: http://pypi.python.org/pypi/motor

.. _pip: http://pip-installer.org

.. _PyMongo: http://pypi.python.org/pypi/pymongo/
