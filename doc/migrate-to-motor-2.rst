Motor 2.0 Migration Guide
=========================

.. currentmodule:: motor.motor_tornado

Motor 2.0 brings a number of changes to Motor 1.0's API. The major version is
required in order to update the session API to support multi-document
transactions, introduced in MongoDB 4.0; this feature is so valuable that it
motivated me to make the breaking change and bump the version number to 2.0.
Since this is the first major version number in almost two years, it removes a
large number of APIs that have been deprecated in the time since Motor 1.0.

Follow this guide to migrate an existing application that had used Motor 1.x.

Check compatibility
-------------------

Read the :doc:`requirements` page and ensure your MongoDB server and Python
interpreter are compatible, and your Tornado version if you are using Tornado.
If you use aiohttp, upgrade to at least 3.0.

Upgrade to Motor 1.3
--------------------

The first step in migrating to Motor 2.0 is to upgrade to at least Motor 1.3.
If your project has a
requirements.txt file, add the line::

  motor >= 1.3, < 2.0

Enable Deprecation Warnings
---------------------------

Starting with Motor 1.3, :exc:`DeprecationWarning` is raised by most methods
removed in Motor 2.0. Make sure you enable runtime warnings to see where
deprecated functions and methods are being used in your application::

  python -Wd <your application>

Warnings can also be changed to errors::

  python -Wd -Werror <your application>

Migrate from deprecated APIs
----------------------------

The following features are deprecated by PyMongo and scheduled for removal;
they are now deleted from Motor:

  - ``MotorClient.kill_cursors`` and ``close_cursor``.
    Allow :class:`MotorCursor` to handle its own cleanup.
  - ``MotorClient.get_default_database``. Call :meth:`MotorClient.get_database`
    with a database name of ``None`` for the same effect.
  - ``MotorDatabase.add_son_manipulator``. Transform documents to and from
    their MongoDB representations in your application code instead.

  - The server command ``getLastError`` and related commands are deprecated,
    their helper functions are deleted from Motor:

    - ``MotorDatabase.last_status``
    - ``MotorDatabase.error``
    - ``MotorDatabase.previous_error``
    - ``MotorDatabase.reset_error_history``

    Use acknowledged writes and rely on Motor to raise exceptions.

  - The server command ``parallelCollectionScan`` is deprecated and
    ``MotorCollection.parallel_scan`` is removed. Use a regular
    :meth:`MotorCollection.find` cursor.
  - ``MotorClient.database_names``. Use
    :meth:`~MotorClient.list_database_names`.
  - ``MotorDatabase.eval``. The server command is deprecated but
    still available with ``MotorDatabase.command("eval", ...)``.
  - ``MotorDatabase.group``. The server command is deprecated but
    still available with ``MotorDatabase.command("group", ...)``.
  - ``MotorDatabase.authenticate`` and ``MotorDatabase.logout``. Add credentials
    to the URI or ``MotorClient`` options instead of calling ``authenticate``.
    To authenticate as multiple users on the same database, instead of using
    ``authenticate`` and ``logout`` use a separate client for each user.
  - ``MotorCollection.initialize_unordered_bulk_op``,
    ``initialize_unordered_bulk_op``, and ``MotorBulkOperationBuilder``. Use
    :meth:`MotorCollection.bulk_write``, see :ref:`Bulk Writes Tutorial
    <bulk-write-tutorial>`.
  - ``MotorCollection.count``. Use :meth:`~MotorCollection.count_documents` or
    :meth:`~MotorCollection.estimated_document_count`.
  - ``MotorCollection.ensure_index``. Use
    :meth:`MotorCollection.create_indexes`.
  - Deprecated write methods have been deleted from :class:`MotorCollection`.

    - ``save`` and ``insert``:  Use :meth:`~MotorCollection.insert_one` or
      :meth:`~MotorCollection.insert_many`.
    - ``update``:  Use :meth:`~MotorCollection.update_one`,
      :meth:`~MotorCollection.update_many`, or
      :meth:`~MotorCollection.replace_one`.
    - ``remove``:  Use :meth:`~MotorCollection.delete_one` or
      :meth:`~MotorCollection.delete_many`.
    - ``find_and_modify``: Use :meth:`~MotorCollection.find_one_and_update`,
      :meth:`~MotorCollection.find_one_and_replace`, or
      :meth:`~MotorCollection.find_one_and_delete`.

  - ``MotorCursor.count`` and ``MotorGridOutCursor.count``. Use
    :meth:`MotorCollection.count_documents` or
    :meth:`MotorCollection.estimated_document_count`.

Migrate from the original callback API
--------------------------------------

Motor was first released before Tornado had introduced Futures, generator-based
coroutines, and the ``yield`` syntax, and long before the async features
developed during Python 3's career. Therefore Motor's original asynchronous API
used callbacks:

.. code-block:: python3

  def callback(result, error):
      if error:
          print(error)
      else:
          print(result)

  collection.find_one({}, callback=callback)

Callbacks have been largely superseded by a Futures API intended for use with
coroutines, see :doc:`tutorial-tornado`. You can still use callbacks with Motor when
appropriate but you must add the callback to a Future instead of passing it as
a parameter:

.. code-block:: python3

  def callback(future):
      try:
          result = future.result()
          print(result)
      except Exception as exc:
          print(exc)

  future = collection.find_one({})
  future.add_done_callback(callback)

The :meth:`~asyncio.Future.add_done_callback` call can be placed on the same
line:

.. code-block:: python3

  collection.find_one({}).add_done_callback(callback)

In almost all cases the modern coroutine API is more readable and provides
better exception handling:

.. code-block:: python3

  async def do_find():
      try:
          result = await collection.find_one({})
          print(result)
      except Exception as exc:
          print(exc)

Upgrade to Motor 2.0
--------------------

Once your application runs without deprecation warnings with Motor 1.3, upgrade
to Motor 2.0. Update any calls in your code to
:meth:`MotorClient.start_session` or
:meth:`~pymongo.client_session.ClientSession.end_session` to handle the
following change.

:meth:`MotorClient.start_session` is a coroutine
------------------------------------------------

In the past, you could use a client session like:

.. code-block:: python3

  session = client.start_session()
  doc = await client.db.collection.find_one({}, session=session)
  session.end_session()

Or:

.. code-block:: python3

  with client.start_session() as session:
     doc = client.db.collection.find_one({}, session=session)

To support multi-document transactions, in Motor 2.0
:meth:`MotorClient.start_session` is a coroutine, not a regular method. It must
be used like ``await client.start_session()`` or ``async with await
client.start_session()``. The coroutine now returns a new class
:class:`~motor.motor_tornado.MotorClientSession`, not PyMongo's
:class:`~pymongo.client_session.ClientSession`. The ``end_session`` method on
the returned :class:`~motor.motor_tornado.MotorClientSession` is also now a
coroutine instead of a regular method. Use it like:

.. code-block:: python3

  session = await client.start_session()
  doc = await client.db.collection.find_one({}, session=session)
  await session.end_session()

Or:

.. code-block:: python3

  async with client.start_session() as session:
     doc = await client.db.collection.find_one({}, session=session)
