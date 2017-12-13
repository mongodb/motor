===============
Developer Guide
===============

Some explanations for those who would like to contribute to Motor development.

Compatibility
-------------

Motor supports the asyncio module in the standard library of Python 3.4 and
later.
Motor also works with Tornado 4.5 and later along with all the Python versions
it supports.

Motor is single-source compatible with all supported Python versions, although
there are some tricks for Python 3. There is some code for the ``async``
and ``await`` features of Python 3.5+ that is conditionally compiled with ``eval``
in ``core.py``.

In ``setup.py`` there are tricks to conditionally import tests depending on
Python version. ``setup.py`` also avoids installing the ``frameworks/asyncio``
directory in a Python 2 environment.

Frameworks
----------

Motor abstracts the differences between Tornado and asyncio by wrapping each in a "framework" interface. A Motor framework
is a module implementing these properties and functions:

- ``CLASS_PREFIX``
- ``add_future``
- ``call_soon``
- ``check_event_loop``
- ``coroutine``
- ``future_or_callback``
- ``get_event_loop``
- ``get_future``
- ``is_event_loop``
- ``is_future``
- ``pymongo_class_wrapper``
- ``run_on_executor``
- ``yieldable``

See the ``frameworks/tornado`` and ``frameworks/asyncio`` modules.

A framework-specific class, like ``MotorClient`` for Tornado or
``AsyncIOMotorClient`` for asyncio, is created by the
``create_class_with_framework`` function, which combines a framework with a
framework-agnostic class, in this case ``AgnosticClient``.

Wrapping PyMongo
----------------

For each PyMongo class, Motor declares an equivalent framework-agnostic class.
For example, the ``AgnosticClient`` class is a framework-agnostic equivalent to
PyMongo's ``MongoClient``. This agnostic class declares each method and property
of the PyMongo class that it intends to wrap. These methods and properties
begin life as type ``MotorAttributeFactory``.

When ``create_class_with_framework`` creates a framework-specific class from an
agnostic class, it creates methods and properties for that class which wrap the
equivalent PyMongo methods and properties.

For example, the ``AgnosticClient`` class declares that ``drop_database`` is an
``AsyncCommand``, which is a subclass of
``MotorAttributeFactory``. At import time, ``create_class_with_framework`` calls
the ``create_attribute`` method of each ``MotorAttributeFactory`` on the
``AgnosticClient``, which results in framework-specific implementations of each
method and property. So at import time, ``create_class_with_framework`` generates
framework-specific wrappers of ``drop_database`` for ``MotorClient`` and
``AsyncIOMotorClient``. These wrappers use framework-specific features to run the
``drop_database`` method asynchronously.

Asynchronization
----------------

This is the heart of Motor's implementation. The ``create_attribute`` method for
asynchronous methods like ``drop_database`` wraps the equivalent PyMongo method
in a Motor method. This wrapper method uses either the Tornado or asyncio
framework to:

- get a reference to the framework's event loop
- start the PyMongo method on a thread in the global ``ThreadPoolExecutor``
- create a ``Future`` that will be resolved by the event loop when the thread finishes
- returns the ``Future`` to the caller

This is what allows Tornado or asyncio coroutines to call Motor methods with
``yield``, ``yield from``, or ``await`` to await I/O without blocking the event loop.

Synchro
-------

A common kind of bug in Motor arises when PyMongo adds a feature, like a new
method or new optional behavior, which we forget to wrap with Motor.

Since PyMongo adds a test to its suite for each new feature, we could catch
these omissions by applying PyMongo's latest tests to Motor. Then a missing
method or feature would cause an obvious test failure. But PyMongo is
synchronous and Motor is async; how can Motor pass PyMongo's tests?

Synchro is a hacky little module that re-synchronizes all Motor methods using
the Tornado IOLoop's ``run_sync`` method. ``synchrotest.py`` overrides the Python
interpreter's import machinery to allow Synchro to masquerade as PyMongo, and
runs PyMongo's test suite against it. Use ``tox -e synchro`` to check out
PyMongo test suite and run it with Synchro.
