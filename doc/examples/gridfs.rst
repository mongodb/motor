Motor GridFS Examples
=====================

.. seealso:: :doc:`../api/web`

Writing a file to GridFS with :meth:`~motor.MotorGridFS.put`
------------------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.MotorClient().open_sync().test

    @gen.engine
    def write_file():
        fs = yield motor.Op(motor.MotorGridFS(db).open)

        # file_id is the ObjectId of the resulting file
        file_id = yield motor.Op(fs.put, 'Contents')

        # put() can take a file or a file-like object, too
        from cStringIO import StringIO
        file_like = StringIO('Lengthy contents')
        file_id = yield motor.Op(fs.put, file_like)

        # Specify the _id
        specified_id = yield motor.Op(fs.put, 'Contents', _id=42)
        assert 42 == specified_id

Streaming a file to GridFS with :class:`~motor.MotorGridIn`
-----------------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.MotorClient().open_sync().test

    @gen.engine
    def write_file_streaming():
        fs = yield motor.Op(motor.MotorGridFS(db).open)

        # Create a MotorGridIn and write in chunks, then close the file to flush
        # all data to the server.
        gridin = yield motor.Op(fs.new_file)
        yield motor.Op(gridin.write, 'First part\n')
        yield motor.Op(gridin.write, 'Second part')
        yield motor.Op(gridin.close)

        # By default, the MotorGridIn's _id is an ObjectId
        file_id = gridin._id

        gridout = yield motor.Op(fs.get, file_id)
        content = yield motor.Op(gridout.read)
        assert 'First part\nSecond part' == content

        # Specify the _id
        gridin = yield motor.Op(fs.new_file, _id=42)
        assert 42 == gridin._id

        # MotorGridIn can write from file-like objects, too
        file = open('my_file.txt')
        yield motor.Op(gridin.write, file)
        yield motor.Op(gridin.close)

.. _setting-attributes-on-a-motor-gridin:

Setting attributes on a :class:`~motor.MotorGridIn`
---------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.MotorClient().open_sync().test

    @gen.engine
    def set_attributes():
        fs = yield motor.Op(motor.MotorGridFS(db).open)
        gridin = yield motor.Op(fs.new_file)

        # Set metadata attributes
        yield motor.Op(gridin.set, 'content_type', 'image/png')
        yield motor.Op(gridin.close)

        # Attributes set after closing are sent to the server immediately
        yield motor.Op(gridin.set, 'my_field', 'my_value')

        gridout = yield motor.Op(fs.get, gridin._id)
        assert 'image/png' == gridin.content_type
        assert 'image/png' == gridin.contentType # synonymous
        assert 'my_value' == gridin.my_field

.. _reading-from-gridfs:

Reading from GridFS with :class:`~motor.MotorGridOut`
-----------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.MotorClient().open_sync().test

    @gen.engine
    def read_file(file_id):
        fs = yield motor.Op(motor.MotorGridFS(db).open)

        # Create a MotorGridOut and read it all at once
        gridout = yield motor.Op(fs.get, file_id)
        content = yield motor.Op(gridout.read)

        # Or read in chunks - every chunk_size bytes is one MongoDB document
        # in the db.fs.chunks collection
        gridout = yield motor.Op(fs.get, file_id)
        content = ''
        while len(content) < gridout.length:
            content += (yield motor.Op(gridout.read, gridout.chunk_size))

        # Get a file by name
        gridout = yield motor.Op(fs.get_last_version, filename='my_file')
        content = yield motor.Op(gridout.read)

.. TODO: examples of static-url generation
