# Copyright 2016 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals


get_database_doc = """
Get a :class:`MotorDatabase` with the given name and options.

Useful for creating a :class:`MotorDatabase` with different codec options,
read preference, and/or write concern from this :class:`MotorClient`.

  >>> from pymongo import ReadPreference
  >>> client.read_preference == ReadPreference.PRIMARY
  True
  >>> db1 = client.test
  >>> db1.read_preference == ReadPreference.PRIMARY
  True
  >>> db2 = client.get_database(
  ...     'test', read_preference=ReadPreference.SECONDARY)
  >>> db2.read_preference == ReadPreference.SECONDARY
  True

:Parameters:
  - `name`: The name of the database - a string.
  - `codec_options` (optional): An instance of
    :class:`~bson.codec_options.CodecOptions`. If ``None`` (the
    default) the :attr:`codec_options` of this :class:`MongoClient` is
    used.
  - `read_preference` (optional): The read preference to use. If
    ``None`` (the default) the :attr:`read_preference` of this
    :class:`MongoClient` is used. See :mod:`~pymongo.read_preferences`
    for options.
  - `write_concern` (optional): An instance of
    :class:`~pymongo.write_concern.WriteConcern`. If ``None`` (the
    default) the :attr:`write_concern` of this :class:`MongoClient` is
    used.
"""

bulk_write_doc = """Send a batch of write operations to the server.

Requests are passed as a list of write operation instances imported
from :mod:`pymongo`:
:class:`~pymongo.operations.InsertOne`,
:class:`~pymongo.operations.UpdateOne`,
:class:`~pymongo.operations.UpdateMany`,
:class:`~pymongo.operations.ReplaceOne`,
:class:`~pymongo.operations.DeleteOne`, or
:class:`~pymongo.operations.DeleteMany`).

For example, say we have these documents::

  {'x': 1, '_id': ObjectId('54f62e60fba5226811f634ef')}
  {'x': 1, '_id': ObjectId('54f62e60fba5226811f634f0')}

We can insert a document, delete one, and replace one like so::

  # DeleteMany, UpdateOne, and UpdateMany are also available.
  from pymongo import InsertOne, DeleteOne, ReplaceOne

  async def modify_data():
      requests = [InsertOne({'y': 1}), DeleteOne({'x': 1}),
                  ReplaceOne({'w': 1}, {'z': 1}, upsert=True)]
      result = await db.test.bulk_write(requests)

      print("inserted %d, deleted %d, modified %d" % (
          result.inserted_count, result.deleted_count, result.modified_count))

      print("upserted_ids: %s" % result.upserted_ids)

      print("collection:")
      async for doc in db.test.find():
          print(doc)

This will print something like::

  inserted 1, deleted 1, modified 0
  upserted_ids: {2: ObjectId('54f62ee28891e756a6e1abd5')}

  collection:
  {'x': 1, '_id': ObjectId('54f62e60fba5226811f634f0')}
  {'y': 1, '_id': ObjectId('54f62ee2fba5226811f634f1')}
  {'z': 1, '_id': ObjectId('54f62ee28891e756a6e1abd5')}

:Parameters:
  - `requests`: A list of write operations (see examples above).
  - `ordered` (optional): If ``True`` (the default) requests will be
    performed on the server serially, in the order provided. If an error
    occurs all remaining operations are aborted. If ``False`` requests
    will be performed on the server in arbitrary order, possibly in
    parallel, and all operations will be attempted.
  - `bypass_document_validation`: (optional) If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  An instance of :class:`~pymongo.results.BulkWriteResult`.

.. seealso:: :ref:`writes-and-ids`

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added session parameter.
"""

create_indexes_doc = """Create one or more indexes on this collection::

  from pymongo import IndexModel, ASCENDING, DESCENDING

  async def create_two_indexes():
      index1 = IndexModel([("hello", DESCENDING),
                           ("world", ASCENDING)], name="hello_world")
      index2 = IndexModel([("goodbye", DESCENDING)])
      print(await db.test.create_indexes([index1, index2]))

This prints::

  ['hello_world', 'goodbye_-1']

:Parameters:
  - `indexes`: A list of :class:`~pymongo.operations.IndexModel`
    instances.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): optional arguments to the createIndexes
    command (like maxTimeMS) can be passed as keyword arguments.

The :attr:`~pymongo.collection.Collection.write_concern` of
this collection is automatically applied to this operation when using
MongoDB >= 3.4.

.. versionchanged:: 1.2
   Added session parameter.
"""

cmd_doc = """Issue a MongoDB command.

Send command ``command`` to the database and return the
response. If ``command`` is a string then the command ``{command: value}``
will be sent. Otherwise, ``command`` must be a
:class:`dict` and will be sent as-is.

Additional keyword arguments are added to the final
command document before it is sent.

For example, a command like ``{buildinfo: 1}`` can be sent
using::

    result = yield db.command("buildinfo")

For a command where the value matters, like ``{collstats:
collection_name}`` we can do::

    result = yield db.command("collstats", collection_name)

For commands that take additional arguments we can use
kwargs. So ``{filemd5: object_id, root: file_root}`` becomes::

    result = yield db.command("filemd5", object_id, root=file_root)

:Parameters:
  - `command`: document representing the command to be issued,
    or the name of the command (for simple commands only).

    .. note:: the order of keys in the `command` document is
       significant (the "verb" must come first), so commands
       which require multiple keys (e.g. `findandmodify`)
       should use an instance of :class:`~bson.son.SON` or
       a string and kwargs instead of a Python :class:`dict`.

  - `value` (optional): value to use for the command verb when
    `command` is passed as a string
  - `check` (optional): check the response for errors, raising
    :class:`~pymongo.errors.OperationFailure` if there are any
  - `allowable_errors`: if `check` is ``True``, error messages
    in this list will be ignored by error-checking
  - `read_preference`: The read preference for this operation.
    See :mod:`~pymongo.read_preferences` for options.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): additional keyword arguments will
    be added to the command document before it is sent

.. versionchanged:: 1.2
   Added session parameter.

.. mongodoc:: commands
"""

delete_many_doc = """Delete one or more documents matching the filter.

If we have a collection with 3 documents like ``{'x': 1}``, then::

  async def clear_collection():
      result = await db.test.delete_many({'x': 1})
      print(result.deleted_count)

This deletes all matching documents and prints "3".

:Parameters:
  - `filter`: A query that matches the documents to delete.
  - `collation` (optional): An instance of
    :class:`~pymongo.collation.Collation`. This option is only supported
    on MongoDB 3.4 and above.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.DeleteResult`.

.. versionchanged:: 1.2
   Added session parameter.
"""

delete_one_doc = """Delete a single document matching the filter.

If we have a collection with 3 documents like ``{'x': 1}``, then::

  async def clear_collection():
      result = await db.test.delete_one({'x': 1})
      print(result.deleted_count)

This deletes one matching document and prints "1".

:Parameters:
  - `filter`: A query that matches the document to delete.
  - `collation` (optional): An instance of
    :class:`~pymongo.collation.Collation`. This option is only supported
    on MongoDB 3.4 and above.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.DeleteResult`.

.. versionchanged:: 1.2
   Added session parameter.
"""

drop_doc = """Alias for ``drop_collection``.

The following two calls are equivalent::

  await db.foo.drop()
  await db.drop_collection("foo")
"""


exists_doc = """Check if a file exists.

The file to check for can be specified by the value of its
``_id`` key, or by passing in a query document. A query
document can be passed in as dictionary, or by using keyword
arguments. Thus, the following three calls are equivalent::

  await fs.exists(file_id)
  await fs.exists({"_id": file_id})
  await fs.exists(_id=file_id)

As are the following two calls::

  await fs.exists({"filename": "mike.txt"})
  await fs.exists(filename="mike.txt")

And the following two::

  await fs.exists({"foo": {"$gt": 12}})
  await fs.exists(foo={"$gt": 12})

Returns ``True`` if a matching file exists, ``False``
otherwise. Calls to :meth:`exists` will not automatically
create appropriate indexes; application developers should be
sure to create indexes if needed and as appropriate.

:Parameters:
  - `document_or_id` (optional): query document, or _id of the
    document to check for
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): keyword arguments are used as a
    query document, if they're present.

.. versionchanged:: 1.2
   Added session parameter.
"""


find_one_doc = """Get a single document from the database.

All arguments to :meth:`find` are also valid arguments for
:meth:`find_one`, although any `limit` argument will be
ignored. Returns a single document, or ``None`` if no matching
document is found.

The :meth:`find_one` method obeys the :attr:`read_preference` of
this Motor collection instance.

:Parameters:

  - `filter` (optional): a dictionary specifying
    the query to be performed OR any other type to be used as
    the value for a query for ``"_id"``.
  - `*args` (optional): any additional positional arguments
    are the same as the arguments to :meth:`find`.
  - `**kwargs` (optional): any additional keyword arguments
    are the same as the arguments to :meth:`find`.
  - `max_time_ms` (optional): a value for max_time_ms may be
    specified as part of `**kwargs`, e.g.:

  .. code-block:: python3

      await collection.find_one(max_time_ms=100)

.. versionchanged:: 1.2
   Added session parameter.
"""

find_one_and_delete_doc = """Finds a single document and deletes it, returning 
the document.

If we have a collection with 2 documents like ``{'x': 1}``, then this code
retrieves and deletes one of them::

  async def delete_one_document():
      print(await db.test.count({'x': 1}))
      doc = await db.test.find_one_and_delete({'x': 1})
      print(doc)
      print(await db.test.count({'x': 1}))

This outputs something like::

  2
  {'x': 1, '_id': ObjectId('54f4e12bfba5220aa4d6dee8')}
  1

If multiple documents match *filter*, a *sort* can be applied. Say we have 3
documents like::

  {'x': 1, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}

This code retrieves and deletes the document with the largest ``_id``::

  async def delete_with_largest_id():
      doc = await db.test.find_one_and_delete(
          {'x': 1}, sort=[('_id', pymongo.DESCENDING)])

This deletes one document and prints it::

  {'x': 1, '_id': 2}

The *projection* option can be used to limit the fields returned::

  async def delete_and_return_x():
      db.test.find_one_and_delete({'x': 1}, projection={'_id': False})

This prints::

  {'x': 1}

:Parameters:
  - `filter`: A query that matches the document to delete.
  - `projection` (optional): a list of field names that should be
    returned in the result document or a mapping specifying the fields
    to include or exclude. If `projection` is a list "_id" will
    always be returned. Use a mapping to exclude fields from
    the result (e.g. projection={'_id': False}).
  - `sort` (optional): a list of (key, direction) pairs
    specifying the sort order for the query. If multiple documents
    match the query, they are sorted and the first is deleted.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): additional command arguments can be passed
    as keyword arguments (for example maxTimeMS can be used with
    recent server versions).

This command uses the :class:`~pymongo.write_concern.WriteConcern` of this
:class:`~pymongo.collection.Collection` when connected to MongoDB >= 3.2. Note
that using an elevated write concern with this command may be slower compared
to using the default write concern.

.. versionchanged:: 1.2
   Added session parameter.
"""

find_one_and_replace_doc = """Finds a single document and replaces it, returning
either the original or the replaced document.

The :meth:`find_one_and_replace` method differs from
:meth:`find_one_and_update` by replacing the document matched by
*filter*, rather than modifying the existing document.

Say we have 3 documents like::

  {'x': 1, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}

Replace one of them like so::

  async def replace_one_doc():
      original_doc = await db.test.find_one_and_replace({'x': 1}, {'y': 1})
      print("original: %s" % original_doc)
      print("collection:")
      async for doc in db.test.find():
          print(doc)

This will print::

  original: {'x': 1, '_id': 0}
  collection:
  {'y': 1, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}

:Parameters:
  - `filter`: A query that matches the document to replace.
  - `replacement`: The replacement document.
  - `projection` (optional): A list of field names that should be
    returned in the result document or a mapping specifying the fields
    to include or exclude. If `projection` is a list "_id" will
    always be returned. Use a mapping to exclude fields from
    the result (e.g. projection={'_id': False}).
  - `sort` (optional): a list of (key, direction) pairs
    specifying the sort order for the query. If multiple documents
    match the query, they are sorted and the first is replaced.
  - `upsert` (optional): When ``True``, inserts a new document if no
    document matches the query. Defaults to ``False``.
  - `return_document`: If
    :attr:`ReturnDocument.BEFORE` (the default),
    returns the original document before it was replaced, or ``None``
    if no document matches. If
    :attr:`ReturnDocument.AFTER`, returns the replaced
    or inserted document.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): additional command arguments can be passed
    as keyword arguments (for example maxTimeMS can be used with
    recent server versions).

This command uses the :class:`~pymongo.write_concern.WriteConcern` of this
:class:`~pymongo.collection.Collection` when connected to MongoDB >= 3.2. Note
that using an elevated write concern with this command may be slower compared
to using the default write concern.

.. versionchanged:: 1.2
   Added session parameter.
"""


find_one_and_update_doc = """Finds a single document and updates it, returning
either the original or the updated document. By default
:meth:`find_one_and_update` returns the original version of
the document before the update was applied::

  async def set_done():
      print(await db.test.find_one_and_update(
          {'_id': 665}, {'$inc': {'count': 1}, '$set': {'done': True}}))

This outputs::
  
  {'_id': 665, 'done': False, 'count': 25}}

To return the updated version of the document instead, use the
*return_document* option. ::

  from pymongo import ReturnDocument

  async def increment_by_userid():
      print(await db.example.find_one_and_update(
          {'_id': 'userid'},
          {'$inc': {'seq': 1}},
          return_document=ReturnDocument.AFTER))

This prints::

  {'_id': 'userid', 'seq': 1}

You can limit the fields returned with the *projection* option. ::

  async def increment_by_userid():
      print(await db.example.find_one_and_update(
          {'_id': 'userid'},
          {'$inc': {'seq': 1}},
          projection={'seq': True, '_id': False},
          return_document=ReturnDocument.AFTER))

This results in::

  {'seq': 2}

The *upsert* option can be used to create the document if it doesn't
already exist. ::

  async def increment_by_userid():
      print(await db.example.find_one_and_update(
          {'_id': 'userid'},
          {'$inc': {'seq': 1}},
          projection={'seq': True, '_id': False},
          upsert=True,
          return_document=ReturnDocument.AFTER))

The result::

  {'seq': 1}

If multiple documents match *filter*, a *sort* can be applied.
Say we have these two documents::

  {'_id': 665, 'done': True, 'result': {'count': 26}}
  {'_id': 701, 'done': True, 'result': {'count': 17}}

Then to update the one with the great ``_id``::

  async def set_done():
      print(await db.test.find_one_and_update(
          {'done': True},
          {'$set': {'final': True}},
          sort=[('_id', pymongo.DESCENDING)]))

This would print::

  {'_id': 701, 'done': True, 'result': {'count': 17}}

:Parameters:
  - `filter`: A query that matches the document to update.
  - `update`: The update operations to apply.
  - `projection` (optional): A list of field names that should be
    returned in the result document or a mapping specifying the fields
    to include or exclude. If `projection` is a list "_id" will
    always be returned. Use a dict to exclude fields from
    the result (e.g. projection={'_id': False}).
  - `sort` (optional): a list of (key, direction) pairs
    specifying the sort order for the query. If multiple documents
    match the query, they are sorted and the first is updated.
  - `upsert` (optional): When ``True``, inserts a new document if no
    document matches the query. Defaults to ``False``.
  - `return_document`: If
    :attr:`ReturnDocument.BEFORE` (the default),
    returns the original document before it was updated, or ``None``
    if no document matches. If
    :attr:`ReturnDocument.AFTER`, returns the updated
    or inserted document.
  - `array_filters` (optional): A list of filters specifying which
    array elements an update should apply. Requires MongoDB 3.6+.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `**kwargs` (optional): additional command arguments can be passed
    as keyword arguments (for example maxTimeMS can be used with
    recent server versions).

This command uses the
:class:`~pymongo.write_concern.WriteConcern` of this
:class:`~pymongo.collection.Collection` when connected to MongoDB >=
3.2. Note that using an elevated write concern with this command may
be slower compared to using the default write concern.

.. versionchanged:: 1.2
   Added array_filters and session parameters.
"""

index_information_doc = """Get information on this collection's indexes.

Returns a dictionary where the keys are index names (as
returned by create_index()) and the values are dictionaries
containing information about each index. The dictionary is
guaranteed to contain at least a single key, ``"key"`` which
is a list of (key, direction) pairs specifying the index (as
passed to create_index()). It will also contain any other
metadata about the indexes, except for the ``"ns"`` and
``"name"`` keys, which are cleaned. For example::

  async def create_x_index():
      print(await db.test.ensure_index("x", unique=True))
      print(await db.test.index_information())

This prints::

  'x_1'
  {'_id_': {'key': [('_id', 1)]},
   'x_1': {'unique': True, 'key': [('x', 1)]}}

.. versionchanged:: 1.2
   Added session parameter.
"""

insert_many_doc = """Insert an iterable of documents. ::

  async def insert_2_docs():
      result = db.test.insert_many([{'x': i} for i in range(2)])
      result.inserted_ids

This prints something like::

  [ObjectId('54f113fffba522406c9cc20e'), ObjectId('54f113fffba522406c9cc20f')]

:Parameters:
  - `documents`: A iterable of documents to insert.
  - `ordered` (optional): If ``True`` (the default) documents will be
    inserted on the server serially, in the order provided. If an error
    occurs all remaining inserts are aborted. If ``False``, documents
    will be inserted on the server in arbitrary order, possibly in
    parallel, and all document inserts will be attempted.
  - `bypass_document_validation`: (optional) If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  An instance of :class:`~pymongo.results.InsertManyResult`.

.. seealso:: :ref:`writes-and-ids`

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added session parameter.
"""


insert_one_doc = """Insert a single document. ::

  async def insert_x():
      result = await db.test.insert_one({'x': 1})
      print(result.inserted_id)

This code outputs the new document's ``_id``::

  ObjectId('54f112defba522406c9cc208')

:Parameters:
  - `document`: The document to insert. Must be a mutable mapping
    type. If the document does not have an _id field one will be
    added automatically.
  - `bypass_document_validation`: (optional) If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.InsertOneResult`.

.. seealso:: :ref:`writes-and-ids`

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added session parameter.
"""


mr_doc = """Perform a map/reduce operation on this collection.

If `full_response` is ``False`` (default) returns a
:class:`MotorCollection` instance containing
the results of the operation. Otherwise, returns the full
response from the server to the `map reduce command`_.

:Parameters:
  - `map`: map function (as a JavaScript string)
  - `reduce`: reduce function (as a JavaScript string)
  - `out`: output collection name or `out object` (dict). See
    the `map reduce command`_ documentation for available options.
    Note: `out` options are order sensitive. :class:`~bson.son.SON`
    can be used to specify multiple options.
    e.g. SON([('replace', <collection name>), ('db', <database name>)])
  - `full_response` (optional): if ``True``, return full response to
    this command - otherwise just return the result collection
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.
  - `callback` (optional): function taking (result, error), executed when
    operation completes.
  - `**kwargs` (optional): additional arguments to the
    `map reduce command`_ may be passed as keyword arguments to this
    helper method, e.g.::

       result = yield db.test.map_reduce(map, reduce, "myresults", limit=2)

If a callback is passed, returns None, else returns a Future.

.. note:: The :meth:`map_reduce` method does **not** obey the
   :attr:`read_preference` of this :class:`MotorCollection`. To run
   mapReduce on a secondary use the :meth:`inline_map_reduce`
   method instead.

.. _map reduce command: http://docs.mongodb.org/manual/reference/command/mapReduce/

.. mongodoc:: mapreduce

.. versionchanged:: 1.2
   Added session parameter.
"""


replace_one_doc = """Replace a single document matching the filter.

Say our collection has one document::

  {'x': 1, '_id': ObjectId('54f4c5befba5220aa4d6dee7')}

Then to replace it with another::

  async def_replace_x_with_y():
      result = await db.test.replace_one({'x': 1}, {'y': 1})
      print('matched %d, modified %d' %
          (result.matched_count, result.modified_count))

      print('collection:')
      async for doc in db.test.find():
          print(doc)

This prints::

  matched 1, modified 1
  collection:
  {'y': 1, '_id': ObjectId('54f4c5befba5220aa4d6dee7')}

The *upsert* option can be used to insert a new document if a matching
document does not exist::

  async def_replace_or_upsert():
      result = await db.test.replace_one({'x': 1}, {'x': 1}, True)
      print('matched %d, modified %d, upserted_id %r' %
          (result.matched_count, result.modified_count, result.upserted_id))

      print('collection:')
      async for doc in db.test.find():
          print(doc)

This prints::

  matched 1, modified 1, upserted_id ObjectId('54f11e5c8891e756a6e1abd4')
  collection:
  {'y': 1, '_id': ObjectId('54f4c5befba5220aa4d6dee7')}

:Parameters:
  - `filter`: A query that matches the document to replace.
  - `replacement`: The new document.
  - `upsert` (optional): If ``True``, perform an insert if no documents
    match the filter.
  - `bypass_document_validation`: (optional) If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `collation` (optional): An instance of
    :class:`~pymongo.collation.Collation`. This option is only supported
    on MongoDB 3.4 and above.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.UpdateResult`.

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added session parameter.
"""


update_doc = """Update a document(s) in this collection.

**DEPRECATED** - Use :meth:`replace_one`, :meth:`update_one`, or
:meth:`update_many` instead."""


update_many_doc = """Update one or more documents that match the filter.

Say our collection has 3 documents::

  {'x': 1, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}
  
We can add 3 to each "x" field::

  async def add_3_to_x():
    result = await db.test.update_many({'x': 1}, {'$inc': {'x': 3}})
    print('matched %d, modified %d' % 
          (result.matched_count, result.modified_count))

    print('collection:')
    async for doc in db.test.find():
        print(doc)

This prints::

  matched 3, modified 3
  collection:
  {'x': 4, '_id': 0}
  {'x': 4, '_id': 1}
  {'x': 4, '_id': 2}

:Parameters:
  - `filter`: A query that matches the documents to update.
  - `update`: The modifications to apply.
  - `upsert` (optional): If ``True``, perform an insert if no documents
    match the filter.
  - `bypass_document_validation` (optional): If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `collation` (optional): An instance of
    :class:`~pymongo.collation.Collation`. This option is only supported
    on MongoDB 3.4 and above.
  - `array_filters` (optional): A list of filters specifying which
    array elements an update should apply. Requires MongoDB 3.6+.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.UpdateResult`.

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added array_filters and session parameters.
"""


update_one_doc = """Update a single document matching the filter.

Say our collection has 3 documents::

  {'x': 1, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}

We can add 3 to the "x" field of one of the documents::

  async def add_3_to_x():
    result = await db.test.update_one({'x': 1}, {'$inc': {'x': 3}})
    print('matched %d, modified %d' %
          (result.matched_count, result.modified_count))

    print('collection:')
    async for doc in db.test.find():
        print(doc)

This prints::

  matched 1, modified 1
  collection:
  {'x': 4, '_id': 0}
  {'x': 1, '_id': 1}
  {'x': 1, '_id': 2}

:Parameters:
  - `filter`: A query that matches the document to update.
  - `update`: The modifications to apply.
  - `upsert` (optional): If ``True``, perform an insert if no documents
    match the filter.
  - `bypass_document_validation`: (optional) If ``True``, allows the
    write to opt-out of document level validation. Default is
    ``False``.
  - `collation` (optional): An instance of
    :class:`~pymongo.collation.Collation`. This option is only supported
    on MongoDB 3.4 and above.
  - `array_filters` (optional): A list of filters specifying which
    array elements an update should apply. Requires MongoDB 3.6+.
  - `session` (optional): a
    :class:`~pymongo.client_session.ClientSession`, created with
    :meth:`~MotorClient.start_session`.

:Returns:
  - An instance of :class:`~pymongo.results.UpdateResult`.

.. note:: `bypass_document_validation` requires server version
  **>= 3.2**

.. versionchanged:: 1.2
   Added array_filters and session parameters.
"""


cursor_sort_doc = """Sorts this cursor's results.

Pass a field name and a direction, either
:data:`~pymongo.ASCENDING` or :data:`~pymongo.DESCENDING`:

.. testsetup:: sort

  MongoClient().test.test_collection.drop()
  MongoClient().test.test_collection.insert_many([
      {'_id': i, 'field1': i % 2, 'field2': i}
      for i in range(5)])
  collection = MotorClient().test.test_collection

.. doctest:: sort

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find().sort('_id', pymongo.DESCENDING)
  ...     docs = yield cursor.to_list(None)
  ...     print([d['_id'] for d in docs])
  ...
  >>> IOLoop.current().run_sync(f)
  [4, 3, 2, 1, 0]

To sort by multiple fields, pass a list of (key, direction) pairs:

.. doctest:: sort

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find().sort([
  ...         ('field1', pymongo.ASCENDING),
  ...         ('field2', pymongo.DESCENDING)])
  ...
  ...     docs = yield cursor.to_list(None)
  ...     print([(d['field1'], d['field2']) for d in docs])
  ...
  >>> IOLoop.current().run_sync(f)
  [(0, 4), (0, 2), (0, 0), (1, 3), (1, 1)]

Beginning with MongoDB version 2.6, text search results can be
sorted by relevance:

.. testsetup:: sort_text

  MongoClient().test.test_collection.drop()
  MongoClient().test.test_collection.insert_many([
      {'field': 'words'},
      {'field': 'words about some words'}])

  MongoClient().test.test_collection.create_index([('field', 'text')])
  collection = MotorClient().test.test_collection

.. doctest:: sort_text

  >>> @gen.coroutine
  ... def f():
  ...     cursor = collection.find({
  ...         '$text': {'$search': 'some words'}},
  ...         {'score': {'$meta': 'textScore'}})
  ...
  ...     # Sort by 'score' field.
  ...     cursor.sort([('score', {'$meta': 'textScore'})])
  ...     docs = yield cursor.to_list(None)
  ...     for doc in docs:
  ...         print('%.1f %s' % (doc['score'], doc['field']))
  ...
  >>> IOLoop.current().run_sync(f)
  1.5 words about some words
  1.0 words

Raises :class:`~pymongo.errors.InvalidOperation` if this cursor has
already been used. Only the last :meth:`sort` applied to this
cursor has any effect.

:Parameters:
  - `key_or_list`: a single key or a list of (key, direction)
    pairs specifying the keys to sort on
  - `direction` (optional): only used if `key_or_list` is a single
    key, if not given :data:`~pymongo.ASCENDING` is assumed
"""

start_session_doc = """
Start a logical session.

This method takes the same parameters as PyMongo's
:class:`~pymongo.client_session.SessionOptions`. See the
:mod:`~pymongo.client_session` module for details.

.. code-block:: python3

  async def coro():
      collection = client.db.collection
  
      with (await client.start_session()) as s:
          doc = {'_id': ObjectId(), 'x': 1}
          await collection.insert_one(doc, session=s)

          secondary = collection.with_options(
              read_preference=ReadPreference.SECONDARY)
  
          # Sessions are causally consistent by default, we can read the doc
          # we just inserted, even reading from a secondary. 
          async for doc in secondary.find(session=s):
              print(doc)

Do **not** use the same session for multiple operations concurrently.

Requires MongoDB 3.6. It is an error to call :meth:`start_session`
if this client has been authenticated to multiple databases using the
deprecated method :meth:`~pymongo.database.Database.authenticate`.

A :class:`~pymongo.client_session.ClientSession` may only be used with
the MongoClient that started it.
  
:Returns:
  An instance of :class:`~pymongo.client_session.ClientSession`.

.. versionadded:: 1.2
"""
