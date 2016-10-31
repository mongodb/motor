.. currentmodule:: motor.motor_tornado

Motor GridFS Examples
=====================

These examples describe using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

.. seealso:: :doc:`../api-tornado/web`

Writing a file to GridFS with :meth:`~MotorGridFS.put`
------------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.motor_tornado.MotorClient().test

    @gen.coroutine
    def write_file():
        fs = motor.motor_tornado.MotorGridFS(db)

        # file_id is the ObjectId of the resulting file.
        file_id = yield fs.put('Contents')

        # put() can take a file or a file-like object, too.
        from cStringIO import StringIO
        file_like = StringIO('Lengthy contents')
        file_id = yield fs.put(file_like)

        # Specify the _id.
        specified_id = yield fs.put('Contents', _id=42)
        assert 42 == specified_id

Streaming a file to GridFS with :class:`MotorGridIn`
----------------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.motor_tornado.MotorClient().test

    @gen.coroutine
    def write_file_streaming():
        fs = motor.motor_tornado.MotorGridFS(db)

        # Create a MotorGridIn and write in chunks, then close the file to
        # flush all data to the server.
        gridin = yield fs.new_file()
        yield gridin.write('First part\n')
        yield gridin.write('Second part')
        yield gridin.close()

        # By default, the MotorGridIn's _id is an ObjectId.
        file_id = gridin._id

        gridout = yield fs.get(file_id)
        content = yield gridout.read()
        assert 'First part\nSecond part' == content

        # Specify the _id.
        gridin = yield fs.new_file(_id=42)
        assert 42 == gridin._id

        # MotorGridIn can write from file-like objects, too.
        file = open('my_file.txt')
        yield gridin.write(file)
        yield gridin.close()

In a Python 3.5 native coroutine, the "async with" statement calls
:meth:`~MotorGridIn.close` automatically::

    async def write_file_streaming():
        fs = motor.motor_tornado.MotorGridFS(db)
        async with await fs.new_file() as gridin:
            await gridin.write(b'First part\n')
            await gridin.write(b'Second part')

        # gridin is now closed automatically.

.. _setting-attributes-on-a-motor-gridin:

Setting attributes on a :class:`MotorGridIn`
--------------------------------------------

.. code-block:: python

    from tornado import gen
    import motor

    db = motor.motor_tornado.MotorClient().test

    @gen.coroutine
    def set_attributes():
        fs = motor.motor_tornado.MotorGridFS(db)
        gridin = yield fs.new_file()

        # Set metadata attributes.
        yield gridin.set('content_type', 'image/png')
        yield gridin.close()

        # Attributes set after closing are sent to the server immediately.
        yield gridin.set('my_field', 'my_value')

        gridout = yield fs.get(gridin._id)
        assert 'image/png' == gridin.content_type
        assert 'image/png' == gridin.contentType  # Synonymous.
        assert 'my_value' == gridin.my_field

.. _reading-from-gridfs:

Reading from GridFS with :class:`MotorGridOut`
----------------------------------------------

.. code-block:: python

    import sys

    from tornado import gen
    import motor

    db = motor.motor_tornado.MotorClient().test

    @gen.coroutine
    def read_file(file_id):
        fs = motor.motor_tornado.MotorGridFS(db)

        # Create a MotorGridOut and read it all at once.
        gridout = yield fs.get(file_id)
        content = yield gridout.read()

        # Get a file by name.
        gridout = yield fs.get_last_version(filename='my_file')
        content = yield gridout.read()

        # Or read in chunks - each chunk is one document in db.fs.chunks.
        gridout = yield fs.get(file_id)

        while True:
            chunk = yield gridout.readchunk()
            if not chunk:
                break
            sys.stdout.write(chunk)

        sys.stdout.flush()

Reading a chunk at a time is much simpler with a Python 3 native coroutine::

    async def read_file(file_id):
        fs = motor.motor_tornado.MotorGridFS(db)
        gridout = await fs.get(file_id)

        async for chunk in gridout:
            sys.stdout.write(chunk)

        sys.stdout.flush()

.. TODO: examples of static-url generation
