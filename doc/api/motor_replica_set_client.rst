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
  .. automotorattribute:: seeds
  .. automotorattribute:: hosts
  .. automotorattribute:: arbiters
  .. automotorattribute:: primary
  .. automotorattribute:: secondaries
  .. automotorattribute:: read_preference
  .. automotorattribute:: tag_sets
  .. automotorattribute:: secondary_acceptable_latency_ms
  .. automotorattribute:: max_pool_size
  .. automotorattribute:: document_class
  .. automotorattribute:: tz_aware
  .. automotorattribute:: safe
  .. method:: sync_client

     Get a :class:`~pymongo.mongo_replica_set_client.MongoReplicaSetClient`
     with the same configuration as this :class:`MotorReplicaSetClient`

  .. automotormethod:: get_lasterror_options
  .. automotormethod:: set_lasterror_options
  .. automotormethod:: unset_lasterror_options
  .. automotormethod:: database_names
  .. automotormethod:: drop_database
  .. automotormethod:: copy_database(from_name, to_name[, from_host=None[, username=None[, password=None[, callback=None]]]])
  .. automotormethod:: close_cursor
