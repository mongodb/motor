Changelog
=========

Next release
------------

**Highlights**

* Dropped Python 2.5 support (since Tornado 3.0 has dropped it)

* Removed ``MotorCursor.tail`` method; it was complex, diverged from PyMongo's
  feature set, and encouraged overuse of MongoDB capped collections as message
  queues when a purpose-built message queue is more appropriate. An example of
  tailing a capped collection is provided: :doc:`examples/tailable-cursors`.

**Bugfixes**

* MotorReplicaSetClient.open() threw error if called without callback
