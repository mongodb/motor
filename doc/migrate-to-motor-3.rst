Motor 3.0 Migration Guide
=========================

.. currentmodule:: motor.motor_tornado

Motor 3.0 brings a number of changes to Motor 2.0's API. The major version is
required in order to bring support for PyMongo 4.0+.
Since this is the first major version number in almost four years, it removes some APIs that have been deprecated in the time since Motor 2.0.
Some of the underlying behaviors and method arguments have changed in PyMongo
4.0 as well.  We highlight some of them below.

Follow this guide to migrate an existing application that had used Motor 2.x.

Check compatibility
-------------------

Read the :doc:`requirements` page and ensure your MongoDB server and Python
interpreter are compatible, and your Tornado version if you are using Tornado.

Upgrade to Motor 2.5
--------------------

The first step in migrating to Motor 3.0 is to upgrade to at least Motor 2.5.
If your project has a
requirements.txt file, add the line::

  motor >= 2.5, < 3.0

Enable Deprecation Warnings
---------------------------

A :exc:`DeprecationWarning` is raised by most methods
removed in Motor 3.0. Make sure you enable runtime warnings to see where
deprecated functions and methods are being used in your application::

  python -Wd <your application>

Warnings can also be changed to errors::

  python -Wd -Werror <your application>

Migrate from deprecated APIs
----------------------------

UUID things
methods deleted
behavioral changes
directConnection


Upgrade to Motor 3.0
--------------------

Once your application runs without deprecation warnings with Motor 2.5, upgrade
to Motor 3.0.
