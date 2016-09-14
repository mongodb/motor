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
Get a `MotorDatabase` with the given name and options.

Useful for creating a `MotorDatabase` with different codec options,
read preference, and/or write concern from this `MotorClient`.

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
       a string and kwargs instead of a Python `dict`.

  - `value` (optional): value to use for the command verb when
    `command` is passed as a string
  - `check` (optional): check the response for errors, raising
    :class:`~pymongo.errors.OperationFailure` if there are any
  - `allowable_errors`: if `check` is ``True``, error messages
    in this list will be ignored by error-checking
  - `read_preference`: The read preference for this operation.
    See :mod:`~pymongo.read_preferences` for options.
  - `**kwargs` (optional): additional keyword arguments will
    be added to the command document before it is sent

.. mongodoc:: commands
"""

mr_doc = """Perform a map/reduce operation on this collection.

If `full_response` is ``False`` (default) returns a
`MotorCollection` instance containing
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
  - `callback` (optional): function taking (result, error), executed when
    operation completes.
  - `**kwargs` (optional): additional arguments to the
    `map reduce command`_ may be passed as keyword arguments to this
    helper method, e.g.::

       result = yield db.test.map_reduce(map, reduce, "myresults", limit=2)

If a callback is passed, returns None, else returns a Future.

.. note:: The :meth:`map_reduce` method does **not** obey the
   :attr:`read_preference` of this `MotorCollection`. To run
   mapReduce on a secondary use the `inline_map_reduce` method
   instead.

.. _map reduce command: http://docs.mongodb.org/manual/reference/command/mapReduce/

.. mongodoc:: mapreduce
"""


# PyMongo's Collection.update shows examples that don't apply to Motor.
update_doc = """Update a document(s) in this collection.

Raises :class:`TypeError` if either `spec` or `document` is
not an instance of ``dict`` or `upsert` is not an instance of
``bool``.

Write concern options can be passed as keyword arguments, overriding
any global defaults. Valid options include w=<int/string>,
wtimeout=<int>, j=<bool>, or fsync=<bool>. See the parameter list below
for a detailed explanation of these options.

There are many useful `update modifiers`_ which can be used
when performing updates. For example, here we use the
``"$set"`` modifier to modify a field in a matching document:

  >>> @gen.coroutine
  ... def do_update():
  ...     result = yield collection.update({'_id': 10},
  ...                                      {'$set': {'x': 1}})

:Parameters:
  - `spec`: a ``dict`` or :class:`~bson.son.SON` instance
    specifying elements which must be present for a document
    to be updated
  - `document`: a ``dict`` or :class:`~bson.son.SON`
    instance specifying the document to be used for the update
    or (in the case of an upsert) insert - see docs on MongoDB
    `update modifiers`_
  - `upsert` (optional): perform an upsert if ``True``
  - `manipulate` (optional): manipulate the document before
    updating? If ``True`` all instances of
    :mod:`~pymongo.son_manipulator.SONManipulator` added to
    this :class:`~pymongo.database.Database` will be applied
    to the document before performing the update.
  - `check_keys` (optional): check if keys in `document` start
    with '$' or contain '.', raising
    :class:`~pymongo.errors.InvalidName`. Only applies to
    document replacement, not modification through $
    operators.
  - `safe` (optional): **DEPRECATED** - Use `w` instead.
  - `multi` (optional): update all documents that match
    `spec`, rather than just the first matching document. The
    default value for `multi` is currently ``False``, but this
    might eventually change to ``True``. It is recommended
    that you specify this argument explicitly for all update
    operations in order to prepare your code for that change.
  - `w` (optional): (integer or string) If this is a replica set, write
    operations will block until they have been replicated to the
    specified number or tagged set of servers. `w=<int>` always includes
    the replica set primary (e.g. w=3 means write to the primary and wait
    until replicated to **two** secondaries). **Passing w=0 disables
    write acknowledgement and all other write concern options.**
  - `wtimeout` (optional): (integer) Used in conjunction with `w`.
    Specify a value in milliseconds to control how long to wait for
    write propagation to complete. If replication does not complete in
    the given timeframe, a timeout exception is raised.
  - `j` (optional): If ``True`` block until write operations have been
    committed to the journal. Ignored if the server is running without
    journaling.
  - `fsync` (optional): If ``True`` force the database to fsync all
    files before returning. When used with `j` the server awaits the
    next group commit before returning.

:Returns:
  - A document (dict) describing the effect of the update.

.. _update modifiers: http://www.mongodb.org/display/DOCS/Updating

.. mongodoc:: update"""


cursor_sort_doc = """
Sorts this cursor's results.

Pass a field name and a direction, either
:data:`~pymongo.ASCENDING` or :data:`~pymongo.DESCENDING`:

.. testsetup:: sort

  MongoClient().test.test_collection.drop()
  MongoClient().test.test_collection.insert([
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
  MongoClient().test.test_collection.insert([
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

