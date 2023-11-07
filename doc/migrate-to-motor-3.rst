Motor 3.0 Migration Guide
=========================

.. currentmodule:: motor.motor_tornado

Motor 3.0 brings a number of changes to Motor 2.0's API. The major version is
required in order to bring support for PyMongo 4.0+.
To add compatibility with PyMongo 4, several methods were removed, as detailed below.
Some of the underlying behaviors and method arguments have changed in PyMongo
4.0 as well.

Follow this guide to migrate an existing application that had used Motor 2.x.

Check compatibility
-------------------

Read the :doc:`requirements` page and ensure your MongoDB server and Python
interpreter are compatible, and your Tornado version if you are using Tornado.

Upgrade to Motor 2.5
--------------------

The first step in migrating to Motor 3.0 is to upgrade to at least Motor 2.5.
If your project has a
``requirements.txt`` file, add the line::

  motor >= 2.5, < 3.0

Python 3.7+
-----------
Motor 3.0 drops support for Python 3.5 and 3.6. Users who wish to upgrade to 3.x must first upgrade to Python 3.7+.

Enable Deprecation Warnings
---------------------------

A :exc:`DeprecationWarning` is raised by most changes made in PyMongo 4.0.
Make sure you enable runtime warnings to see where
deprecated functions and methods are being used in your application::

  python -Wd <your application>

Warnings can also be changed to errors::

  python -Wd -Werror <your application>

Note that there are some deprecation warnings raised by Motor itself for
APIs that are deprecated but not yet removed, like :meth:`~motor.motor_tornado.MotorCursor.fetch_next`.

MotorClient
-----------

``directConnection`` defaults to False
......................................

``directConnection`` URI option and keyword argument to :class:`~motor
.MotorClient` defaults to ``False`` instead of ``None``,
allowing for the automatic discovery of replica sets. This means that if you
want a direct connection to a single server you must pass
``directConnection=True`` as a URI option or keyword argument.

Renamed URI options
...................

Several deprecated URI options have been renamed to the standardized
option names defined in the
`URI options specification <https://github.com/mongodb/specifications/blob/master/source/uri-options/uri-options.rst>`_.
The old option names and their renamed equivalents are summarized in the table
below. Some renamed options have different semantics from the option being
replaced as noted in the 'Migration Notes' column.

+--------------------+-------------------------------+--------------------------------------------------------+
| Old URI Option     | Renamed URI Option            | Migration Notes                                        |
+====================+===============================+========================================================+
| ssl_pem_passphrase | tlsCertificateKeyFilePassword | -                                                      |
+--------------------+-------------------------------+--------------------------------------------------------+
| ssl_ca_certs       | tlsCAFile                     | -                                                      |
+--------------------+-------------------------------+--------------------------------------------------------+
| ssl_crlfile        | tlsCRLFile                    | -                                                      |
+--------------------+-------------------------------+--------------------------------------------------------+
| ssl_match_hostname | tlsAllowInvalidHostnames      | ``ssl_match_hostname=True`` is equivalent to           |
|                    |                               | ``tlsAllowInvalidHostnames=False`` and vice-versa.     |
+--------------------+-------------------------------+--------------------------------------------------------+
| ssl_cert_reqs      | tlsAllowInvalidCertificates   | Instead of ``ssl.CERT_NONE``, ``ssl.CERT_OPTIONAL``    |
|                    |                               | and ``ssl.CERT_REQUIRED``, the new option expects      |
|                    |                               | a boolean value - ``True`` is equivalent to            |
|                    |                               | ``ssl.CERT_NONE``, while ``False`` is equivalent to    |
|                    |                               | ``ssl.CERT_REQUIRED``.                                 |
+--------------------+-------------------------------+--------------------------------------------------------+
| ssl_certfile       | tlsCertificateKeyFile         | Instead of using ``ssl_certfile`` and ``ssl_keyfile``  |
|                    |                               | to specify the certificate and private key files       |
+--------------------+                               | respectively,  use ``tlsCertificateKeyFile`` to pass   |
| ssl_keyfile        |                               | a single file containing both the client certificate   |
|                    |                               | and the private key.                                   |
+--------------------+-------------------------------+--------------------------------------------------------+
| j                  | journal                       | -                                                      |
+--------------------+-------------------------------+--------------------------------------------------------+
| wtimeout           | wTimeoutMS                    | -                                                      |
+--------------------+-------------------------------+--------------------------------------------------------+

MotorClient.fsync is removed
............................

Removed :meth:`~motor.motor_tornado.MotorClient.fsync`. Run the
`fsync command`_ directly with :meth:`~motor.motor_tornado.MotorDatabase.command`
instead. For example::

    await client.admin.command('fsync', lock=True)

.. _fsync command: https://mongodb.com/docs/manual/reference/command/fsync/

MotorClient.unlock is removed
.............................

Removed :meth:`~motor.motor_tornado.MotorClient.unlock`. Run the
`fsyncUnlock command`_ directly with
:meth:`~motor.motor_tornado.MotorDatabase.command` instead. For example::

     await client.admin.command('fsyncUnlock')

.. _fsyncUnlock command: https://mongodb.com/docs/manual/reference/command/fsyncUnlock/


MotorClient.max_bson_size/max_message_size/max_write_batch_size are removed
...........................................................................

Removed :attr:`~motor.motor_tornado.MotorClient.max_bson_size`,
:attr:`~motor.motor_tornado.MotorClient.max_message_size`, and
:attr:`~motor.motor_tornado.MotorClient.max_write_batch_size`. These helpers
were incorrect when in ``loadBalanced=true mode`` and ambiguous in clusters
with mixed versions. Use the `hello command`_ to get the authoritative
value from the remote server instead. Code like this::

    max_bson_size = client.max_bson_size
    max_message_size = client.max_message_size
    max_write_batch_size = client.max_write_batch_size

can be changed to this::

    doc = await client.admin.command('hello')
    max_bson_size = doc['maxBsonObjectSize']
    max_message_size = doc['maxMessageSizeBytes']
    max_write_batch_size = doc['maxWriteBatchSize']

.. _hello command: https://mongodb.com/docs/manual/reference/command/hello/

MotorClient.event_listeners and other configuration option helpers are removed
..............................................................................

The following client configuration option helpers are removed:

- :attr:`~motor.motor_tornado.MotorClient.event_listeners`.
- :attr:`~motor.motor_tornado.MotorClient.max_pool_size`.
- :attr:`~motor.motor_tornado.MotorClient.min_pool_size`.
- :attr:`~motor.motor_tornado.MotorClient.max_idle_time_ms`.
- :attr:`~motor.motor_tornado.MotorClient.local_threshold_ms`.
- :attr:`~motor.motor_tornado.MotorClient.server_selection_timeout`.
- :attr:`~motor.motor_tornado.MotorClient.retry_writes`.
- :attr:`~motor.motor_tornado.MotorClient.retry_reads`.

These helpers have been replaced by
:attr:`~motor.motor_tornado.MotorClient.options`. Code like this::

    client.event_listeners
    client.local_threshold_ms
    client.server_selection_timeout
    client.max_pool_size
    client.min_pool_size
    client.max_idle_time_ms

can be changed to this::

    client.options.event_listeners
    client.options.local_threshold_ms
    client.options.server_selection_timeout
    client.options.pool_options.max_pool_size
    client.options.pool_options.min_pool_size
    client.options.pool_options.max_idle_time_seconds

``tz_aware`` defaults to ``False``
..................................

``tz_aware``, an argument for :class:`~bson.json_util.JSONOptions`,
now defaults to ``False`` instead of ``True``. ``json_util.loads`` now
decodes datetime as naive by default.

MotorClient cannot execute operations after ``close()``
.......................................................

:class:`~motor.motor_tornado.MotorClient` cannot execute any operations
after being closed. The previous behavior would simply reconnect. However,
now you must create a new instance.

MotorClient raises exception when given more than one URI
.........................................................

:class:`~motor.motor_tornado.MotorClient` now raises a :exc:`~pymongo.errors.ConfigurationError`
when more than one URI is passed into the ``hosts`` argument.

MotorClient raises exception when given unescaped percent sign in login info
............................................................................

:class:`~motor.motor_tornado.MotorClient` now raises an
:exc:`~pymongo.errors.InvalidURI` exception
when it encounters unescaped percent signs in username and password.

Database
--------

MotorDatabase.current_op is removed
...................................

Removed :meth:`~motor.motor_tornado.MotorDatabase.current_op`. Use
:meth:`~motor.motor_tornado.MotorDatabase.aggregate` instead with the
`$currentOp aggregation pipeline stage`_. Code like
this::

    ops = client.admin.current_op()['inprog']

can be changed to this::

    ops = await client.admin.aggregate([{'$currentOp': {}}]).to_list()

.. _$currentOp aggregation pipeline stage: https://mongodb.com/docs/manual/reference/operator/aggregation/currentOp/

MotorDatabase.profiling_level is removed
........................................

Removed :meth:`~motor.motor_tornado.MotorDatabase.profiling_level` which was deprecated in
PyMongo 3.12. Use the `profile command`_ instead. Code like this::

  level = db.profiling_level()

Can be changed to this::

  profile = await db.command('profile', -1)
  level = profile['was']

.. _profile command: https://mongodb.com/docs/manual/reference/command/profile/

MotorDatabase.set_profiling_level is removed
............................................

Removed :meth:`~motor.motor_tornado.MotorDatabase.set_profiling_level` which was deprecated in
PyMongo 3.12. Use the `profile command`_ instead. Code like this::

  db.set_profiling_level(pymongo.ALL, filter={'op': 'query'})

Can be changed to this::

  res = await db.command('profile', 2, filter={'op': 'query'})

MotorDatabase.profiling_info is removed
.......................................

Removed :meth:`~motor.motor_tornado.MotorDatabase.profiling_info` which was deprecated in
PyMongo 3.12. Query the `'system.profile' collection`_ instead. Code like this::

  profiling_info = db.profiling_info()

Can be changed to this::

  profiling_info = await db['system.profile'].find().to_list()

.. _'system.profile' collection: https://mongodb.com/docs/manual/reference/database-profiler/

MotorDatabase.__bool__ raises NotImplementedError
.................................................
:class:`~motor.motor_tornado.MotorDatabase` now raises an error upon evaluating as a
Boolean. Code like this::

  if database:

Can be changed to this::

  if database is not None:

You must now explicitly compare with None.


MotorCollection
---------------

MotorCollection.map_reduce and MotorCollection.inline_map_reduce are removed
............................................................................

Removed :meth:`~motor.motor_tornado.MotorCollection.map_reduce` and
:meth:`~motor.motor_tornado.MotorCollection.inline_map_reduce`.
Migrate to :meth:`~motor.motor_tornado.MotorCollection.aggregate` or run the
`mapReduce command`_ directly with :meth:`~motor.motor_tornado.MotorDatabase.command`
instead. For more guidance on this migration see:

- https://mongodb.com/docs/manual/reference/map-reduce-to-aggregation-pipeline/
- https://mongodb.com/docs/manual/reference/aggregation-commands-comparison/

.. _mapReduce command: https://mongodb.com/docs/manual/reference/command/mapReduce/


MotorCollection.reindex is removed
..................................

Removed :meth:`motor.motor_tornado.MotorCollection.reindex`. Run the
`reIndex command`_ directly instead. Code like this::

  >>> result = await database.my_collection.reindex()

can be changed to this::

  >>> result = await database.command('reIndex', 'my_collection')

.. _reIndex command: https://mongodb.com/docs/manual/reference/command/reIndex/


The modifiers parameter is removed
..................................

Removed the ``modifiers`` parameter from
:meth:`~motor.motor_tornado.MotorCollection.find`,
:meth:`~motor.motor_tornado.MotorCollection.find_one`,
:meth:`~motor.motor_tornado.MotorCollection.find_raw_batches`, and
:meth:`~motor.motor_tornado.MotorCursor`. Pass the options directly to the method
instead. Code like this::

  cursor = await coll.find({}, modifiers={
      "$comment": "comment",
      "$hint": {"_id": 1},
      "$min": {"_id": 0},
      "$max": {"_id": 6},
      "$maxTimeMS": 6000,
      "$returnKey": False,
      "$showDiskLoc": False,
  })

can be changed to this::

  cursor = await coll.find(
      {},
      comment="comment",
      hint={"_id": 1},
      min={"_id": 0},
      max={"_id": 6},
      max_time_ms=6000,
      return_key=False,
      show_record_id=False,
  )

The hint parameter is required with min/max
...........................................

The ``hint`` option is now required when using ``min`` or ``max`` queries
with :meth:`~motor.motor_tornado.MotorCollection.find` to ensure the query utilizes
the correct index. For example, code like this::

  cursor = await coll.find({}, min={'x', min_value})

can be changed to this::

  cursor = await coll.find({}, min={'x', min_value}, hint=[('x', ASCENDING)])

MotorCollection.__bool__ raises NotImplementedError
...................................................
:class:`~motor.motor_tornado.MotorCollection` now raises an error upon evaluating
as a Boolean. Code like this::

  if collection:

Can be changed to this::

  if collection is not None:

You must now explicitly compare with None.

MotorCollection.find returns entire document with empty projection
..................................................................
Empty projections (eg {} or []) for
:meth:`~motor.motor_tornado.MotorCollection.find`, and
:meth:`~motor.motor_tornado.MotorCollection.find_one`
are passed to the server as-is rather than the previous behavior which
substituted in a projection of ``{"_id": 1}``. This means that an empty
projection will now return the entire document, not just the ``"_id"`` field.
To ensure that behavior remains consistent, code like this::

  await coll.find({}, projection={})

Can be changed to this::

  await coll.find({}, projection={"_id":1})


SONManipulator is removed
-------------------------

PyMongo 4.0 removed :mod:`pymongo.son_manipulator`.

Motor 3.0 removed :meth:`motor.MotorDatabase.add_son_manipulator`,
:attr:`motor.MotorDatabase.outgoing_copying_manipulators`,
:attr:`motor.MotorDatabase.outgoing_manipulators`,
:attr:`motor.MotorDatabase.incoming_copying_manipulators`, and
:attr:`motor.MotorDatabase.incoming_manipulators`.

Removed the ``manipulate`` parameter from
:meth:`~motor.motor_tornado.MotorCollection.find`,
:meth:`~motor.motor_tornado.MotorCollection.find_one`, and
:meth:`~motor.motor_tornado.MotorCursor`.

The :class:`pymongo.son_manipulator.SONManipulator` API has limitations as a
technique for transforming your data and was deprecated in PyMongo 3.0.
Instead, it is more flexible and straightforward to transform outgoing
documents in your own code before passing them to PyMongo, and transform
incoming documents after receiving them from PyMongo.

Alternatively, if your application uses the ``SONManipulator`` API to convert
custom types to BSON, the :class:`~bson.codec_options.TypeCodec` and
:class:`~bson.codec_options.TypeRegistry` APIs may be a suitable alternative.
For more information, see the
:external:pymongo:doc:`custom type example <examples/custom_type>`.

GridFS changes
--------------

.. _removed-gridfs-checksum:

disable_md5 parameter is removed
................................

Removed the ``disable_md5`` option for :class:`~motor.motor_tornado.gridfs.MotorGridFSBucket` and
:class:`~motor.motor_tornado.gridfs.MotorGridFS`. GridFS no longer generates checksums.
Applications that desire a file digest should implement it outside GridFS
and store it with other file metadata. For example::

  import hashlib
  my_db = MotorClient().test
  fs = GridFSBucket(my_db)
  grid_in = fs.open_upload_stream("test_file")
  file_data = b'...'
  sha356 = hashlib.sha256(file_data).hexdigest()
  await grid_in.write(file_data)
  grid_in.sha356 = sha356  # Set the custom 'sha356' field
  await grid_in.close()

Note that for large files, the checksum may need to be computed in chunks
to avoid the excessive memory needed to load the entire file at once.

Removed features with no migration path
---------------------------------------

Encoding a UUID raises an error by default
..........................................

The default uuid_representation for :class:`~bson.codec_options.CodecOptions`,
:class:`~bson.json_util.JSONOptions`, and
:class:`~motor.motor_tornado.MotorClient` has been changed from
:data:`bson.binary.UuidRepresentation.PYTHON_LEGACY` to
:data:`bson.binary.UuidRepresentation.UNSPECIFIED`. Attempting to encode a
:class:`uuid.UUID` instance to BSON or JSON now produces an error by default.
See :ref:`handling-uuid-data-example` for details.


Upgrade to Motor 3.0
--------------------

Once your application runs without deprecation warnings with Motor 2.5, upgrade
to Motor 3.0.
