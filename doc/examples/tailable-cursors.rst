.. currentmodule:: motor.motor_tornado

Motor Tailable Cursor Example
=============================

.. important:: This page describes using Motor with Tornado. Beginning in
  version 0.5 Motor can also integrate with asyncio instead of Tornado. The
  documentation is not yet updated for Motor's asyncio integration.

A cursor on a capped collection can be tailed using `MotorCursor.fetch_next`:

.. code-block:: python

    @gen.coroutine
    def tail_example():
        results = []
        collection = db.my_capped_collection
        cursor = collection.find(tailable=True, await_data=True)
        while True:
            if not cursor.alive:
                now = datetime.datetime.utcnow()
                # While collection is empty, tailable cursor dies immediately
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))
                cursor = collection.find(tailable=True, await_data=True)

            if (yield cursor.fetch_next):
                results.append(cursor.next_object())
                print results

.. seealso:: `Tailable cursors <http://docs.mongodb.org/manual/tutorial/create-tailable-cursor/>`_
