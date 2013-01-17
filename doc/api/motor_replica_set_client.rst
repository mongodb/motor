:class:`MotorReplicaSetClient` -- Connection to MongoDB replica set
=======================================================================

.. currentmodule:: motor

.. autoclass:: motor.MotorReplicaSetClient

  .. automethod:: open
  .. automethod:: open_sync
  .. method:: disconnect

     Disconnect from MongoDB.

     Disconnecting will close all underlying sockets in the
     connection pool. If the :class:`MotorReplicaSetClient` is used again it
     will be automatically re-opened.

  .. method:: close

     Alias for :meth:`disconnect`.

  .. describe:: c[db_name] || c.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorReplicaSetClient` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
     Raises :class:`~pymongo.errors.InvalidOperation` if connection isn't opened yet.

  .. autoattribute:: connected
  .. autoattribute:: seeds
  .. autoattribute:: hosts
  .. autoattribute:: arbiters
  .. autoattribute:: primary
  .. autoattribute:: secondaries
  .. autoattribute:: read_preference
  .. autoattribute:: tag_sets
  .. autoattribute:: secondary_acceptable_latency_ms
  .. autoattribute:: max_pool_size
  .. autoattribute:: document_class
  .. autoattribute:: tz_aware
  .. autoattribute:: safe
  .. method:: sync_client

     Get a :class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient`
     with the same configuration as this :class:`MotorReplicaSetClient`

  .. automethod:: get_lasterror_options
  .. automethod:: set_lasterror_options
  .. automethod:: unset_lasterror_options
  .. automethod:: database_names
  .. automethod:: drop_database
  .. automethod:: copy_database(from_name, to_name[, from_host=None[, username=None[, password=None[, callback=None]]]])
  .. automethod:: close_cursor
