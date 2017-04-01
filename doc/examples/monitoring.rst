.. currentmodule:: motor.motor_tornado

Application Performance Monitoring (APM)
========================================

Motor implements the same `Command Monitoring`_ and `Topology Monitoring`_ specifications as other MongoDB drivers.
Therefore, you can register callbacks to be notified of every MongoDB query or command your program sends, and the server's reply to each, as well as getting a notification whenever the driver checks a server's status or detects a change in your replica set.

Motor wraps PyMongo, and it shares PyMongo's API for monitoring. To receive notifications about events, you subclass one of PyMongo's four listener classes, :class:`~pymongo.monitoring.CommandListener`, :class:`~pymongo.monitoring.ServerListener`, :class:`~pymongo.monitoring.TopologyListener`, or :class:`~pymongo.monitoring.ServerHeartbeatListener`.

Command Monitoring
------------------

Subclass :class:`~pymongo.monitoring.CommandListener` to be notified whenever a command starts, succeeds, or fails.

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: command logger start
  :end-before: command logger end

Register an instance of ``MyCommandLogger``:

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: command logger register start
  :end-before: command logger register end

You can register any number of listeners, of any of the four listener types.

Although you use only APIs from PyMongo's :mod:`~pymongo.monitoring` module to configure monitoring, if you create a :class:`MotorClient` its commands are monitored, the same as a PyMongo :class:`~pymongo.mongo_client.MongoClient`.

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: motorclient start
  :end-before: motorclient end

This logs something like:

.. code-block:: text

  Command insert with request id 50073 started on server ('localhost', 27017)
  Command insert with request id 50073 on server ('localhost', 27017)
  succeeded in 362 microseconds

See PyMongo's :mod:`~pymongo.monitoring` module for details about the event data your callbacks receive.

Server and Topology Monitoring
------------------------------

Subclass :class:`~pymongo.monitoring.ServerListener` to be notified whenever Motor detects a change in the state of a MongoDB server it is connected to.

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: server logger start
  :end-before: server logger end

Subclass :class:`~pymongo.monitoring.TopologyListener` to be notified whenever Motor detects a change in the state of your server topology. Examples of such topology changes are a replica set failover, or if you are connected to several mongos servers and one becomes unavailable.

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: topology logger start
  :end-before: topology logger end

Motor monitors MongoDB servers with periodic checks called "heartbeats".
Subclass :class:`~pymongo.monitoring.ServerHeartbeatListener` to be notified whenever Motor begins a server check, and whenever a check succeeds or fails.

.. literalinclude:: monitoring_example.py
  :language: py3
  :start-after: heartbeat logger start
  :end-before: heartbeat logger end

Thread Safety
-------------

Watch out: Your listeners' callbacks are executed on various background threads, *not* the main thread. To interact with Tornado or Motor from a listener callback, you must defer to the main thread using :meth:`IOLoop.add_callback <tornado.ioloop.IOLoop.add_callback>`, which is the only thread-safe :class:`~tornado.ioloop.IOLoop` method. Similarly, if you use asyncio instead of Tornado, defer your action to the main thread with :meth:`~asyncio.AbstractEventLoop.call_soon_threadsafe`. There is probably no need to be concerned about this detail, however: logging is the only reasonable thing to do from a listener, and `the Python logging module is thread-safe <https://docs.python.org/3/library/logging.html#thread-safety>`_.

Further Information
-------------------

See also:

* PyMongo's :mod:`~pymongo.monitoring` module
* `The Command Monitoring Spec`_
* `The Topology Monitoring Spec`_
* The `monitoring.py`_ example file in the Motor repository

.. _The Command Monitoring Spec:
.. _Command Monitoring: https://github.com/mongodb/specifications/blob/master/source/command-monitoring/command-monitoring.rst
.. _The Topology Monitoring Spec:
.. _Topology Monitoring: https://github.com/mongodb/specifications/blob/master/source/server-discovery-and-monitoring/server-discovery-and-monitoring-monitoring.rst
.. _monitoring.py: https://github.com/mongodb/motor/blob/master/doc/examples/monitoring.py
