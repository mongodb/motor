:class:`~motor.motor_asyncio.AsyncIOMotorCollection`
====================================================

.. currentmodule:: motor.motor_asyncio

.. autoclass:: AsyncIOMotorCollection
  :members:
  :exclude-members: create_index, inline_map_reduce

  .. describe:: c[name] || c.name

     Get the `name` sub-collection of :class:`AsyncIOMotorCollection` `c`.

     Raises :class:`~pymongo.errors.InvalidName` if an invalid
     collection name is used.

  .. attribute:: database

  The :class:`AsyncIOMotorDatabase` that this
  :class:`AsyncIOMotorCollection` is a part of.

  .. coroutinemethod:: create_index(self, keys, **kwargs)

      Creates an index on this collection.

      Takes either a single key or a list of (key, direction) pairs.
      The key(s) must be an instance of :class:`basestring`
      (:class:`str` in python 3), and the direction(s) must be one of
      (:data:`~pymongo.ASCENDING`, :data:`~pymongo.DESCENDING`,
      :data:`~pymongo.GEO2D`, :data:`~pymongo.GEOHAYSTACK`,
      :data:`~pymongo.GEOSPHERE`, :data:`~pymongo.HASHED`,
      :data:`~pymongo.TEXT`).

      To create a single key ascending index on the key ``'mike'`` we just
      use a string argument::

        await my_collection.create_index("mike")

      For a compound index on ``'mike'`` descending and ``'eliot'``
      ascending we need to use a list of tuples::

        await my_collection.create_index([("mike", pymongo.DESCENDING),
                                          ("eliot", pymongo.ASCENDING)])

      All optional index creation parameters should be passed as
      keyword arguments to this method. For example::

        await my_collection.create_index([("mike", pymongo.DESCENDING)],
                                         background=True)

      Valid options include, but are not limited to:

        - `name`: custom name to use for this index - if none is
          given, a name will be generated.
        - `unique`: if ``True`` creates a uniqueness constraint on the index.
        - `background`: if ``True`` this index should be created in the
          background.
        - `sparse`: if ``True``, omit from the index any documents that lack
          the indexed field.
        - `bucketSize`: for use with geoHaystack indexes.
          Number of documents to group together within a certain proximity
          to a given longitude and latitude.
        - `min`: minimum value for keys in a :data:`~pymongo.GEO2D`
          index.
        - `max`: maximum value for keys in a :data:`~pymongo.GEO2D`
          index.
        - `expireAfterSeconds`: <int> Used to create an expiring (TTL)
          collection. MongoDB will automatically delete documents from
          this collection after <int> seconds. The indexed field must
          be a UTC datetime or the data will not expire.
        - `partialFilterExpression`: A document that specifies a filter for
          a partial index.
        - `collation` (optional): An instance of
          :class:`~pymongo.collation.Collation`. This option is only supported
          on MongoDB 3.4 and above.

      See the MongoDB documentation for a full list of supported options by
      server version.

      .. warning:: `dropDups` is not supported by MongoDB 3.0 or newer. The
        option is silently ignored by the server and unique index builds
        using the option will fail if a duplicate value is detected.

      .. note:: `partialFilterExpression` requires server version **>= 3.2**

      .. note:: The :attr:`~pymongo.collection.Collection.write_concern` of
         this collection is automatically applied to this operation when using
         MongoDB >= 3.4.

      :Parameters:
        - `keys`: a single key or a list of (key, direction)
          pairs specifying the index to create
        - `**kwargs` (optional): any additional index creation
          options (see the above list) should be passed as keyword
          arguments

      .. mongodoc:: indexes

  .. coroutinemethod:: inline_map_reduce(self, map, reduce, full_response=False, **kwargs)

      Perform an inline map/reduce operation on this collection.

      Perform the map/reduce operation on the server in RAM. A result
      collection is not created. The result set is returned as a list
      of documents.

      If `full_response` is ``False`` (default) returns the
      result documents in a list. Otherwise, returns the full
      response from the server to the `map reduce command`_.

      The :meth:`inline_map_reduce` method obeys the :attr:`read_preference`
      of this :class:`Collection`.

      :Parameters:
        - `map`: map function (as a JavaScript string)
        - `reduce`: reduce function (as a JavaScript string)
        - `full_response` (optional): if ``True``, return full response to
          this command - otherwise just return the result collection
        - `**kwargs` (optional): additional arguments to the
          `map reduce command`_ may be passed as keyword arguments to this
          helper method, e.g.::

            await db.test.inline_map_reduce(map, reduce, limit=2)

      .. _map reduce command: http://docs.mongodb.org/manual/reference/command/mapReduce/

      .. mongodoc:: mapreduce
