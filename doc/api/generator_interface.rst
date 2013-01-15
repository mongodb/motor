.. _generator-interface:

Generator Interface
===================

.. currentmodule:: motor

Motor provides yield points to be used with `tornado.gen
<http://www.tornadoweb.org/documentation/gen.html>`_,
within functions or methods decorated by ``@gen.engine``. See
:ref:`generator-interface-example`.

.. class:: Op

  Subclass of `tornado.gen.Task`_. Runs a single asynchronous MongoDB operation
  and resumes the generator with the result of the operation when it is
  complete.
  :class:`motor.Op` adds an additional convenience to ``Task``:
  it assumes the callback is passed the standard ``result, error`` pair, and if
  ``error`` is not ``None`` then ``Op`` raises the error.
  Otherwise, ``result`` is returned from the ``yield`` expression:

.. code-block:: python

    from tornado import gen

    @gen.engine
    def get_some_documents(db):
        cursor = db.collection.find().limit(10)

        try:
            # to_list is passed a callback, which is later executed with
            # arguments (result, error). If error is not None, it is raised
            # from this line. Otherwise 'result' is the value of the yield
            # expression.
            documents = yield motor.Op(cursor.to_list)
            return documents
        except Exception, e:
            print e

.. class:: WaitOp

  For complex control flows, a :class:`motor.Op` can be split into two
  parts, a `Callback`_ and a :class:`motor.WaitOp`.

.. code-block:: python

    @gen.engine
    def get_some_documents(db):
        cursor = db.collection.find().limit(10)
        cursor.to_list(callback=(yield gen.Callback('key')))
        try:
            documents = yield motor.WaitOp('key')
            return documents
        except Exception, e:
            print e

.. _tornado.gen.Task: http://www.tornadoweb.org/documentation/gen.html#tornado.gen.Task

.. _Callback: http://www.tornadoweb.org/documentation/gen.html#tornado.gen.Callback

.. class:: WaitAllOps

  To wait for multiple Callbacks to complete, yield
  :class:`motor.WaitAllOps`:

.. code-block:: python

    @gen.engine
    def get_two_documents_in_parallel(db, id_one, id_two):
        db.collection.find_one(
            {'_id': id_one}, callback=(yield gen.Callback('one')))

        db.collection.find_one(
            {'_id': id_two}, callback=(yield gen.Callback('two')))

        try:
            document_one, document_two = yield motor.WaitAllOps(['one', 'two'])
            return document_one, document_two
        except Exception, e:
            print e
