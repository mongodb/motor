Motor Tailable Cursor Example
=============================

Motor provides a convenience method :meth:`~motor.MotorCursor.tail`

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

.. seealso:: `Tailable cursors <http://www.mongodb.org/display/DOCS/Tailable+Cursors>`_
