Motor Tailable Cursor Example
=============================

A cursor on a capped collection can be tailed using
:attr:`~motor.MotorCursor.fetch_next`:

.. code-block:: python

    @gen.coroutine
    def tail_example():
        results = []
        collection = db.my_capped_collection
        cursor = collection.find(tailable=True, await_data=True)
        while True:
            if not cursor.alive:
                # While collection is empty, tailable cursor dies immediately
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))
                cursor = collection.find(tailable=True, await_data=True)

            if (yield cursor.fetch_next):
                results.append(cursor.next_object())
                print results

.. seealso:: `Tailable cursors <http://docs.mongodb.org/manual/tutorial/create-tailable-cursor/>`_
