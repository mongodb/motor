Motor 1.0 Migration Guide
=========================

.. currentmodule:: motor.motor_tornado

Motor 1.0 brings a number of backward breaking changes to the pre-1.0 API.
Follow this guide to migrate an existing application that had used an older
version of Motor.

Removed features with no migration path
---------------------------------------

:class:`MotorReplicaSetClient` is removed
..........................................

In Motor 1.0, :class:`MotorClient` is the only class. Connect to a replica set with
a "replicaSet" URI option or parameter::

  MotorClient("mongodb://localhost/?replicaSet=my-rs")
  MotorClient(host, port, replicaSet="my-rs")

The "compile_re" option is removed
..................................

In Motor 1.0 regular expressions are never compiled to Python `re.match`
objects.

Motor 0.7
---------

The first step in migrating to Motor 1.0 is to upgrade to at least Motor 0.7.
If your project has a
requirements.txt file, add the line::

  motor >= 0.7, < 1.0

Most of the key new
methods and options from Motor 1.0 are backported in Motor 0.7 making
migration much easier.

Enable Deprecation Warnings
---------------------------

Starting with Motor 0.7, :exc:`DeprecationWarning` is raised by most methods
removed in Motor 1.0. Make sure you enable runtime warnings to see
where deprecated functions and methods are being used in your application::

  python -Wd <your application>

Warnings can also be changed to errors::

  python -Wd -Werror <your application>

Not all deprecated features raise `DeprecationWarning` when
used. For example, `~motor.motor_tornado.MotorReplicaSetClient` will be
removed in Motor 1.0 but it does not raise `DeprecationWarning`
in Motor 0.7. See also `Removed features with no migration path`_.

CRUD API
--------

Changes to find() and find_one()
................................

"spec" renamed "filter"
~~~~~~~~~~~~~~~~~~~~~~~

The ``spec`` option has been renamed to ``filter``. Code like this::

  cursor = collection.find(spec={"a": 1})

can be changed to this with Motor 0.7 or later::

  cursor = collection.find(filter={"a": 1})

or this with any version of Motor::

  cursor = collection.find({"a": 1})

"fields" renamed "projection"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``fields`` option has been renamed to ``projection``. Code like this::

  cursor = collection.find({"a": 1}, fields={"_id": False})

can be changed to this with Motor 0.7 or later::

  cursor = collection.find({"a": 1}, projection={"_id": False})

or this with any version of Motor::

  cursor = collection.find({"a": 1}, {"_id": False})

"partial" renamed "allow_partial_results"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``partial`` option has been renamed to ``allow_partial_results``. Code like
this::

  cursor = collection.find({"a": 1}, partial=True)

can be changed to this with Motor 0.7 or later::

  cursor = collection.find({"a": 1}, allow_partial_results=True)

"timeout" replaced by "no_cursor_timeout"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``timeout`` option has been replaced by ``no_cursor_timeout``. Code like this::

  cursor = collection.find({"a": 1}, timeout=False)

can be changed to this with Motor 0.7 or later::

  cursor = collection.find({"a": 1}, no_cursor_timeout=True)

"snapshot" and "max_scan" replaced by "modifiers"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``snapshot`` and ``max_scan`` options have been removed. They can now be set,
along with other $ query modifiers, through the ``modifiers`` option. Code like
this::

  cursor = collection.find({"a": 1}, snapshot=True)

can be changed to this with Motor 0.7 or later::

  cursor = collection.find({"a": 1}, modifiers={"$snapshot": True})

or with any version of Motor::

  cursor = collection.find({"$query": {"a": 1}, "$snapshot": True})

"network_timeout" is removed
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``network_timeout`` option has been removed. This option was always the
wrong solution for timing out long running queries and should never be used
in production. Starting with **MongoDB 2.6** you can use the $maxTimeMS query
modifier. Code like this::

  # Set a 5 second select() timeout.
  cursor = collection.find({"a": 1}, network_timeout=5)

can be changed to this with Motor 0.7 or later::

  # Set a 5 second (5000 millisecond) server side query timeout.
  cursor = collection.find({"a": 1}, modifiers={"$maxTimeMS": 5000})

or with any version of Motor::

  cursor = collection.find({"$query": {"a": 1}, "$maxTimeMS": 5000})

.. seealso:: `$maxTimeMS
  <http://docs.mongodb.org/manual/reference/operator/meta/maxTimeMS/>`_

Tailable cursors
~~~~~~~~~~~~~~~~

The ``tailable`` and ``await_data`` options have been replaced by ``cursor_type``.
Code like this::

  cursor = collection.find({"a": 1}, tailable=True)
  cursor = collection.find({"a": 1}, tailable=True, await_data=True)

can be changed to this with Motor 0.7 or later::

  from pymongo import CursorType
  cursor = collection.find({"a": 1}, cursor_type=CursorType.TAILABLE)
  cursor = collection.find({"a": 1}, cursor_type=CursorType.TAILABLE_AWAIT)

Other removed options
~~~~~~~~~~~~~~~~~~~~~

The ``read_preference``, ``tag_sets``,
and ``secondary_acceptable_latency_ms`` options have been removed. See the `Read
Preferences`_ section for solutions.

Read Preferences
----------------

The "read_preference" attribute is immutable
............................................

Code like this::

  from pymongo import ReadPreference
  db = client.my_database
  db.read_preference = ReadPreference.SECONDARY

can be changed to this with Motor 0.7 or later::

  db = client.get_database("my_database",
                           read_preference=ReadPreference.SECONDARY)

Code like this::

  cursor = collection.find({"a": 1},
                           read_preference=ReadPreference.SECONDARY)

can be changed to this with Motor 0.7 or later::

  coll2 = collection.with_options(read_preference=ReadPreference.SECONDARY)
  cursor = coll2.find({"a": 1})

.. seealso:: :meth:`~MotorDatabase.get_collection`

The "tag_sets" option and attribute are removed
...............................................

The ``tag_sets`` MotorClient option is removed. The ``read_preference``
option can be used instead. Code like this::

  client = MotorClient(
      read_preference=ReadPreference.SECONDARY,
      tag_sets=[{"dc": "ny"}, {"dc": "sf"}])

can be changed to this with Motor 0.7 or later::

  from pymongo.read_preferences import Secondary
  client = MotorClient(read_preference=Secondary([{"dc": "ny"}]))

To change the tags sets for a MotorDatabase or MotorCollection, code like this::

  db = client.my_database
  db.read_preference = ReadPreference.SECONDARY
  db.tag_sets = [{"dc": "ny"}]

can be changed to this with Motor 0.7 or later::

  db = client.get_database("my_database",
                           read_preference=Secondary([{"dc": "ny"}]))

Code like this::

  cursor = collection.find(
      {"a": 1},
      read_preference=ReadPreference.SECONDARY,
      tag_sets=[{"dc": "ny"}])

can be changed to this with Motor 0.7 or later::

  from pymongo.read_preferences import Secondary
  coll2 = collection.with_options(
      read_preference=Secondary([{"dc": "ny"}]))
  cursor = coll2.find({"a": 1})

.. seealso:: :meth:`~MotorDatabase.get_collection`

The "secondary_acceptable_latency_ms" option and attribute are removed
......................................................................

Motor 0.x supports ``secondary_acceptable_latency_ms`` as an option to methods
throughout the driver, but mongos only supports a global latency option.
Motor 1.0 has changed to match the behavior of mongos, allowing migration
from a single server, to a replica set, to a sharded cluster without a
surprising change in server selection behavior. A new option,
``localThresholdMS``, is available through MotorClient and should be used in
place of ``secondaryAcceptableLatencyMS``. Code like this::

  client = MotorClient(readPreference="nearest",
                       secondaryAcceptableLatencyMS=100)

can be changed to this with Motor 0.7 or later::

  client = MotorClient(readPreference="nearest",
                       localThresholdMS=100)

Write Concern
-------------

The "write_concern" attribute is immutable
..........................................

The ``write_concern`` attribute is immutable in Motor 1.0. Code like this::

  client = MotorClient()
  client.write_concern = {"w": "majority"}

can be changed to this with any version of Motor::

  client = MotorClient(w="majority")

Code like this::

  db = client.my_database
  db.write_concern = {"w": "majority"}

can be changed to this with Motor 0.7 or later::

  from pymongo import WriteConcern
  db = client.get_database("my_database",
                           write_concern=WriteConcern(w="majority"))

The new CRUD API write methods do not accept write concern options. Code like
this::

  oid = collection.insert({"a": 2}, w="majority")

can be changed to this with Motor 0.7 or later::

  from pymongo import WriteConcern
  coll2 = collection.with_options(
      write_concern=WriteConcern(w="majority"))
  oid = coll2.insert({"a": 2})

.. seealso:: :meth:`~MotorDatabase.get_collection`

Codec Options
-------------

The "document_class" attribute is removed
.........................................

Code like this::

  from bson.son import SON
  client = MotorClient()
  client.document_class = SON

can be replaced by this in any version of Motor::

  from bson.son import SON
  client = MotorClient(document_class=SON)

or to change the ``document_class`` for a :class:`MotorDatabase`
with Motor 0.7 or later::

  from bson.codec_options import CodecOptions
  from bson.son import SON
  db = client.get_database("my_database", CodecOptions(SON))

.. seealso:: :meth:`~MotorDatabase.get_collection` and
  :meth:`~MotorCollection.with_options`

The "uuid_subtype" option and attribute are removed
...................................................

Code like this::

  from bson.binary import JAVA_LEGACY
  db = client.my_database
  db.uuid_subtype = JAVA_LEGACY

can be replaced by this with Motor 0.7 or later::

  from bson.binary import JAVA_LEGACY
  from bson.codec_options import CodecOptions
  db = client.get_database("my_database",
                           CodecOptions(uuid_representation=JAVA_LEGACY))

.. seealso:: :meth:`~MotorDatabase.get_collection` and
  :meth:`~MotorCollection.with_options`

MotorClient
-----------

The ``open`` method
...................

The :meth:`~MotorClient.open` method is removed in Motor 1.0.
Motor clients have opened themselves on demand since Motor 0.2.

The max_pool_size parameter is removed
......................................

Motor 1.0 replaced the max_pool_size parameter with support for the MongoDB URI
``maxPoolSize`` option. Code like this::

  client = MotorClient(max_pool_size=10)

can be replaced by this with Motor 0.7 or later::

  client = MotorClient(maxPoolSize=10)
  client = MotorClient("mongodb://localhost:27017/?maxPoolSize=10")

The "disconnect" method is removed
..................................

Code like this::

  client.disconnect()

can be replaced by this::

  client.close()

The host and port attributes are removed
........................................

Code like this::

  host = client.host
  port = client.port

can be replaced by this with Motor 0.7 or later::

  address = client.address
  host, port = address or (None, None)
