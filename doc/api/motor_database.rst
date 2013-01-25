:class:`MotorDatabase`
======================

.. currentmodule:: motor

.. autoclass:: motor.MotorDatabase

  .. describe:: db[collection_name] || db.collection_name

     Get the `collection_name` :class:`MotorCollection` of
     :class:`MotorDatabase` `db`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid collection name is used.

  .. automethod:: command
  .. automethod:: create_collection
  .. automethod:: drop_collection
  .. automethod:: validate_collection
  .. automethod:: collection_names
  .. automethod:: current_op
  .. automethod:: dereference
  .. automethod:: error
  .. automethod:: previous_error
  .. automethod:: last_status
  .. automethod:: reset_error_history
  .. automethod:: set_profiling_level
  .. automethod:: profiling_level
  .. automethod:: profiling_info
  .. automethod:: eval
  .. automethod:: add_user
  .. automethod:: remove_user
  .. automethod:: authenticate
  .. automethod:: logout
  .. automethod:: add_son_manipulator
  .. autoattribute:: incoming_manipulators
  .. autoattribute:: incoming_copying_manipulators
  .. autoattribute:: outgoing_manipulators
  .. autoattribute:: outgoing_copying_manipulators
  .. autoattribute:: write_concern
  .. autoattribute:: read_preference
  .. autoattribute:: tag_sets
  .. autoattribute:: secondary_acceptable_latency_ms
  .. autoattribute:: slave_okay
  .. automethod:: get_lasterror_options
  .. automethod:: set_lasterror_options
  .. automethod:: unset_lasterror_options
