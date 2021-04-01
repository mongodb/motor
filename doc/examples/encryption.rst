.. _Client-Side Field Level Encryption:

Client-Side Field Level Encryption
==================================

Starting in MongoDB 4.2, client-side field level encryption allows an application
to encrypt specific data fields in addition to pre-existing MongoDB
encryption features such as `Encryption at Rest
<https://dochub.mongodb.org/core/security-encryption-at-rest>`_ and
`TLS/SSL (Transport Encryption)
<https://dochub.mongodb.org/core/security-tls-transport-encryption>`_.

With field level encryption, applications can encrypt fields in documents
*prior* to transmitting data over the wire to the server. Client-side field
level encryption supports workloads where applications must guarantee that
unauthorized parties, including server administrators, cannot read the
encrypted data.

.. mongodoc:: client-side-field-level-encryption

Dependencies
------------

To get started using client-side field level encryption in your project,
you will need to install the
`pymongocrypt <https://pypi.org/project/pymongocrypt/>`_ library
as well as the driver itself. Install both the driver and a compatible
version of pymongocrypt like this::

    $ python -m pip install 'motor[encryption]'

Note that installing on Linux requires pip 19 or later for manylinux2010 wheel
support. For more information about installing pymongocrypt see
`the installation instructions on the project's PyPI page
<https://pypi.org/project/pymongocrypt/>`_.

mongocryptd
-----------

The ``mongocryptd`` binary is required for automatic client-side encryption
and is included as a component in the `MongoDB Enterprise Server package
<https://dochub.mongodb.org/core/install-mongodb-enterprise>`_. For more
information on this binary, see the `PyMongo documentation on mongocryptd
<https://pymongo.readthedocs.io/en/stable/examples/encryption.html>`_.

Automatic Client-Side Field Level Encryption
--------------------------------------------

Automatic client-side field level encryption is enabled by creating a
:class:`~motor.motor_asyncio.AsyncIOMotorClient` with the ``auto_encryption_opts``
option set to an instance of
:class:`~pymongo.encryption_options.AutoEncryptionOpts`. The following
examples show how to setup automatic client-side field level encryption
using :class:`~motor.motor_asyncio.AsyncIOMotorClientEncryption` to create a new
encryption data key.

.. note:: Automatic client-side field level encryption requires MongoDB 4.2+
   enterprise or a MongoDB 4.2+ Atlas cluster. The community version of the
   server supports automatic decryption as well as
   :ref:`explicit-client-side-encryption`.

Providing Local Automatic Encryption Rules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following example shows how to specify automatic encryption rules via the
``schema_map`` option. The automatic encryption rules are expressed using a
`strict subset of the JSON Schema syntax
<https://dochub.mongodb.org/core/client-side-field-level-encryption-automatic-encryption-rules>`_.

Supplying a ``schema_map`` provides more security than relying on
JSON Schemas obtained from the server. It protects against a
malicious server advertising a false JSON Schema, which could trick
the client into sending unencrypted data that should be encrypted.

JSON Schemas supplied in the ``schema_map`` only apply to configuring
automatic client-side field level encryption. Other validation
rules in the JSON schema will not be enforced by the driver and
will result in an error.


.. literalinclude:: auto_csfle_example.py
  :language: python3

Server-Side Field Level Encryption Enforcement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The MongoDB 4.2+ server supports using schema validation to enforce encryption
of specific fields in a collection. This schema validation will prevent an
application from inserting unencrypted values for any fields marked with the
``"encrypt"`` JSON schema keyword.

The following example shows how to setup automatic client-side field level
encryption using
:class:`~motor.motor_asyncio.AsyncIOMotorClientEncryption` to create a new encryption
data key and create a collection with the
`Automatic Encryption JSON Schema Syntax
<https://dochub.mongodb.org/core/client-side-field-level-encryption-automatic-encryption-rules>`_.

.. literalinclude:: server_fle_enforcement_example.py
  :language: python3

.. _explicit-client-side-encryption:

Explicit Encryption
~~~~~~~~~~~~~~~~~~~

Explicit encryption is a MongoDB community feature and does not use the
``mongocryptd`` process. Explicit encryption is provided by the
:class:`~motor.motor_asyncio.AsyncIOMotorClientEncryption` class, for example:

.. literalinclude:: explicit_encryption_example.py
  :language: python3

Explicit Encryption with Automatic Decryption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Although automatic encryption requires MongoDB 4.2 enterprise or a
MongoDB 4.2 Atlas cluster, automatic *decryption* is supported for all users.
To configure automatic *decryption* without automatic *encryption* set
``bypass_auto_encryption=True`` in
:class:`~pymongo.encryption_options.AutoEncryptionOpts`:

.. literalinclude:: explicit_encryption_automatic_decryption_example.py
  :language: python3
