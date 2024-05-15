Installation
============

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
* PyMongo_ >=4.1,<5
* Python 3.8+

Optional dependencies:

Motor supports same optional dependencies as PyMongo. Required dependencies can be installed
along with Motor.

GSSAPI authentication requires ``gssapi`` extra dependency. The correct
dependency can be installed automatically along with Motor::

  $ pip install "motor[gssapi]"

similarly,

`MONGODB-AWS <https://pymongo.readthedocs.io/en/stable/examples/authentication.html#mongodb-aws>`_
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
