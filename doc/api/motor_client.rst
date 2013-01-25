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
  .. autoattribute:: host
  .. autoattribute:: port
  .. autoattribute:: nodes
  .. autoattribute:: max_pool_size
  .. autoattribute:: document_class
  .. autoattribute:: tz_aware
  .. autoattribute:: write_concern
  .. autoattribute:: read_preference
  .. autoattribute:: tag_sets
  .. autoattribute:: secondary_acceptable_latency_ms
  .. autoattribute:: slave_okay
  .. autoattribute:: is_locked
  .. method:: sync_client

     Get a :class:`~pymongo.mongo_client.MongoClient` with the same
     configuration as this :class:`MotorClient`

  .. automethod:: get_lasterror_options
  .. automethod:: set_lasterror_options
  .. automethod:: unset_lasterror_options
  .. automethod:: database_names
  .. automethod:: drop_database
  .. automethod:: copy_database(from_name, to_name[, from_host=None[, username=None[, password=None[, callback=None]]]])
  .. automethod:: server_info
  .. automethod:: close_cursor
  .. automethod:: kill_cursors
  .. automethod:: fsync
  .. automethod:: unlock
  .. automethod:: start_request
  .. automethod:: end_request
