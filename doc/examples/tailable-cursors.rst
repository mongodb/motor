Motor Tailable Cursor Examples
==============================

Motor provides a convenience method :meth:`~motor.MotorCursor.tail`:

.. code-block:: python

    import datetime
    from tornado import ioloop, gen
    import motor

    db = motor.MotorClient().open_sync().test

    @gen.engine
    def tailable_example():
        loop = ioloop.IOLoop.instance()

        yield motor.Op(db.capped_collection.drop)
        yield motor.Op(db.create_collection,
            'capped_collection', capped=True, size=1000, autoIndexId=True)

        results = []

        def each(result, error):
            if error:
                raise error

            results.append(result['i'])

        db.capped_collection.find().tail(callback=each)

        for i in range(3):
            yield motor.Op(db.capped_collection.insert, {'i': i})
            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.5))

        assert range(3) == results

A cursor can also be tailed using :attr:`~motor.MotorCursor.fetch_next`:

.. code-block:: python

    @gen.engine
    def tailable_example_fetch_next():
        results = []
        cursor = capped.find(tailable=True, await_data=True)
        while True:
            if not cursor.alive:
                # While collection is empty, tailable cursor dies immediately
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))
                cursor = capped.find(tailable=True, await_data=True)

            if (yield cursor.fetch_next):
                results.append(cursor.next_object())

.. seealso:: `Tailable cursors <http://www.mongodb.org/display/DOCS/Tailable+Cursors>`_

.. _tornado.gen: http://www.tornadoweb.org/documentation/gen.html