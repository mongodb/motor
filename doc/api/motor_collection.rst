:class:`MotorCollection`
========================

.. currentmodule:: motor

.. autoclass:: MotorCollection

  .. describe:: c[name] || c.name

     Get the `name` sub-collection of :class:`MotorCollection` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid
     collection name is used.

  .. autoattribute:: full_name
  .. autoattribute:: name
  .. attribute:: database

  The :class:`MotorDatabase` that this
  :class:`MotorCollection` is a part of.

  .. autoattribute:: write_concern
  .. autoattribute:: read_preference
  .. autoattribute:: tag_sets
  .. autoattribute:: secondary_acceptable_latency_ms
  .. autoattribute:: slave_okay
  .. autoattribute:: uuid_subtype
  .. automethod:: get_lasterror_options
  .. automethod:: set_lasterror_options
  .. automethod:: unset_lasterror_options
  .. automethod:: insert(doc_or_docs[, manipulate=True[, check_keys=True[, continue_on_error=False[, callback=None [, **kwargs]]]]])
  .. automethod:: save(to_save[, manipulate=True[, callback=None [, **kwargs]]])
  .. automethod:: update(spec, document[, upsert=False[, manipulate=False[, multi=False[, callback=None [, **kwargs]]]])
  .. automethod:: remove([spec_or_id=None[, callback=None [, **kwargs]]])
  .. automethod:: drop
  .. automethod:: find([spec=None[, fields=None[, skip=0[, limit=0[, timeout=True[, snapshot=False[, tailable=False[, sort=None[, max_scan=None[, as_class=None[, slave_okay=False[, await_data=False[, partial=False[, manipulate=True[, read_preference=ReadPreference.PRIMARY[, **kwargs]]]]]]]]]]]]]]]])
  .. automethod:: find_one([spec_or_id=None[, *args[, callback=<function> [, **kwargs]]])
  .. automethod:: count
  .. automethod:: create_index
  .. automethod:: ensure_index
  .. automethod:: drop_index
  .. automethod:: drop_indexes
  .. automethod:: reindex
  .. automethod:: index_information
  .. automethod:: options
  .. automethod:: aggregate
  .. automethod:: group
  .. automethod:: rename
  .. automethod:: distinct
  .. automethod:: map_reduce
  .. automethod:: inline_map_reduce
  .. automethod:: find_and_modify

