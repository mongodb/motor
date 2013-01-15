:class:`MotorDatabase`
======================

.. currentmodule:: motor

.. autoclass:: motor.MotorDatabase

  .. describe:: db[collection_name] || db.collection_name

     Get the `collection_name` :class:`MotorCollection` of
     :class:`MotorDatabase` `db`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid collection name is used.

  .. automotormethod:: command
  .. automotormethod:: create_collection
  .. automotormethod:: drop_collection
  .. automotormethod:: validate_collection
  .. automotormethod:: collection_names
  .. automotormethod:: current_op
  .. automotormethod:: dereference
  .. automotormethod:: error
  .. automotormethod:: previous_error
  .. automotormethod:: last_status
  .. automotormethod:: reset_error_history
  .. automotormethod:: set_profiling_level
  .. automotormethod:: profiling_level
  .. automotormethod:: profiling_info
  .. automotormethod:: eval
  .. automotormethod:: add_user
  .. automotormethod:: remove_user
  .. automotormethod:: authenticate
  .. automotormethod:: logout
  .. automethod:: add_son_manipulator
  .. automotormethod:: incoming_manipulators
  .. automotormethod:: incoming_copying_manipulators
  .. automotormethod:: outgoing_manipulators
  .. automotormethod:: outgoing_copying_manipulators
  .. automotorattribute:: read_preference
  .. automotorattribute:: tag_sets
  .. automotorattribute:: secondary_acceptable_latency_ms
  .. automotorattribute:: slave_okay
  .. automotorattribute:: safe
  .. automotormethod:: get_lasterror_options
  .. automotormethod:: set_lasterror_options
  .. automotormethod:: unset_lasterror_options
