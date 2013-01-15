:class:`MotorClient` -- Connection to MongoDB
=================================================

.. currentmodule:: motor

.. autoclass:: motor.MotorClient

  .. automethod:: open
  .. automethod:: open_sync
  .. method:: disconnect

     Disconnect from MongoDB.

     Disconnecting will close all underlying sockets in the
     connection pool. If the :class:`MotorClient` is used again it
     will be automatically re-opened.

  .. method:: close

     Alias for :meth:`disconnect`.

  .. describe:: c[db_name] || c.db_name

     Get the `db_name` :class:`MotorDatabase` on :class:`MotorClient` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid database name is used.
     Raises :class:`~pymongo.errors.InvalidOperation` if connection isn't opened yet.

  .. automethod:: is_locked
  .. automotorattribute:: host
  .. automotorattribute:: port
  .. automotorattribute:: nodes
  .. automotorattribute:: max_pool_size
  .. automotorattribute:: document_class
  .. automotorattribute:: tz_aware
  .. automotorattribute:: read_preference
  .. automotorattribute:: tag_sets
  .. automotorattribute:: secondary_acceptable_latency_ms
  .. automotorattribute:: slave_okay
  .. automotorattribute:: safe
  .. automotorattribute:: is_locked
  .. method:: sync_client

     Get a :class:`~pymongo.mongo_client.MongoClient` with the same
     configuration as this :class:`MotorClient`

  .. automotormethod:: get_lasterror_options
  .. automotormethod:: set_lasterror_options
  .. automotormethod:: unset_lasterror_options
  .. automotormethod:: database_names
  .. automotormethod:: drop_database
  .. automotormethod:: copy_database(from_name, to_name[, from_host=None[, username=None[, password=None[, callback=None]]]])
  .. automotormethod:: server_info
  .. automotormethod:: close_cursor
  .. automotormethod:: kill_cursors
  .. automotormethod:: fsync
  .. automotormethod:: unlock
  .. automethod:: start_request
  .. automethod:: end_request
