:class:`MotorCollection`
========================

.. currentmodule:: motor

.. autoclass:: MotorCollection

  .. describe:: c[name] || c.name

     Get the `name` sub-collection of :class:`MotorCollection` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid
     collection name is used.

  .. automotorattribute:: full_name
  .. automotorattribute:: name
  .. attribute:: database

  The :class:`MotorDatabase` that this
  :class:`MotorCollection` is a part of.

  .. automotorattribute:: slave_okay
  .. automotorattribute:: read_preference
  .. automotorattribute:: tag_sets
  .. automotorattribute:: secondary_acceptable_latency_ms
  .. automotorattribute:: safe
  .. automotorattribute:: uuid_subtype
  .. automotormethod:: get_lasterror_options
  .. automotormethod:: set_lasterror_options
  .. automotormethod:: unset_lasterror_options
  .. automotormethod:: insert(doc_or_docs[, manipulate=True[, safe=False[, check_keys=True[, continue_on_error=False[, callback=None [, **kwargs]]]]])
  .. automotormethod:: save(to_save[, manipulate=True[, safe=False[, callback=None [, **kwargs]]])
  .. automotormethod:: update(spec, document[, upsert=False[, manipulate=False[, safe=False[, multi=False[, callback=None [, **kwargs]]]]])
  .. automotormethod:: remove([spec_or_id=None[, safe=False[, callback=None [, **kwargs]]])
  .. automotormethod:: drop
  .. automethod:: find([spec=None[, fields=None[, skip=0[, limit=0[, timeout=True[, snapshot=False[, tailable=False[, sort=None[, max_scan=None[, as_class=None[, slave_okay=False[, await_data=False[, partial=False[, manipulate=True[, read_preference=ReadPreference.PRIMARY[, **kwargs]]]]]]]]]]]]]]]])
  .. automotormethod:: find_one([spec_or_id=None[, *args[, callback=<function> [, **kwargs]]])
  .. automotormethod:: count
  .. automotormethod:: create_index
  .. automotormethod:: ensure_index
  .. automotormethod:: drop_index
  .. automotormethod:: drop_indexes
  .. automotormethod:: reindex
  .. automotormethod:: index_information
  .. automotormethod:: options
  .. automotormethod:: aggregate
  .. automotormethod:: group
  .. automotormethod:: rename
  .. automotormethod:: distinct
  .. automotormethod:: map_reduce
  .. automotormethod:: inline_map_reduce
  .. automotormethod:: find_and_modify

