.. currentmodule:: motor.motor_tornado

Motor Tailable Cursor Example
=============================

By default, MongoDB will automatically close a cursor when the client has
exhausted all results in the cursor. However, for capped collections you may
use a tailable cursor that remains open after the client exhausts the results
in the initial cursor.

The following is a basic example of using a tailable cursor to tail the oplog
of a replica set member:

.. code-block:: python

    from asyncio import sleep
    from pymongo.cursor import CursorType

    async def tail_oplog_example():
        oplog = client.local.oplog.rs
        first = await oplog.find().sort('$natural', pymongo.ASCENDING).limit(-1).next()
        print(first)
        ts = first['ts']

        while True:
            # For a regular capped collection CursorType.TAILABLE_AWAIT is the
            # only option required to create a tailable cursor. When querying the
            # oplog, the oplog_replay option enables an optimization to quickly
            # find the 'ts' value we're looking for. The oplog_replay option
            # can only be used when querying the oplog. Starting in MongoDB 4.4
            # this option is ignored by the server as queries against the oplog
            # are optimized automatically by the MongoDB query engine.
            cursor = oplog.find({'ts': {'$gt': ts}},
                                cursor_type=CursorType.TAILABLE_AWAIT,
                                oplog_replay=True)
            while cursor.alive:
                async for doc in cursor:
                    ts = doc['ts']
                    print(doc)
                # We end up here if the find() returned no documents or if the
                # tailable cursor timed out (no new documents were added to the
                # collection for more than 1 second).
                await sleep(1)

.. seealso:: `Tailable cursors <http://docs.mongodb.org/manual/tutorial/create-tailable-cursor/>`_
