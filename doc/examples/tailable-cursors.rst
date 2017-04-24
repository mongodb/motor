.. currentmodule:: motor.motor_tornado

Motor Tailable Cursor Example
=============================

This example describes using Motor with Tornado. Beginning in
version 0.5 Motor can also integrate with asyncio instead of Tornado.

A cursor on a capped collection can be tailed using :meth:`~MotorCursor.fetch_next`:

.. code-block:: python

    @gen.coroutine
    def tail_example():
        results = []
        collection = db.my_capped_collection
        cursor = collection.find(cursor_type=CursorType.TAILABLE, await_data=True)
        while True:
            if not cursor.alive:
                now = datetime.datetime.utcnow()
                # While collection is empty, tailable cursor dies immediately
                yield gen.sleep(1)
                cursor = collection.find(cursor_type=CursorType.TAILABLE, await_data=True)

            if (yield cursor.fetch_next):
                results.append(cursor.next_object())
                print results

.. seealso:: `Tailable cursors <http://docs.mongodb.org/manual/tutorial/create-tailable-cursor/>`_
