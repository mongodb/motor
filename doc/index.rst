Motor: Asynchronous Python driver for MongoDB
=============================================

.. image:: _static/motor.png
    :align: center

About
-----

Motor presents a callback- or Future-based API for non-blocking access to
MongoDB from Tornado_ or asyncio_.

The `source is on GitHub <https://github.com/mongodb/motor>`_ and
the docs are on `ReadTheDocs <http://motor.readthedocs.org/>`_.

    "Motor uses a clever greenlet-based approach to fully support both
    synchronous and asynchronous interfaces from a single codebase. It's great
    to see companies like MongoDB produce first-party asynchronous drivers for
    their products."

    --*Ben Darnell, Tornado maintainer*

Install with::

    $ pip install motor

Post questions about Motor to the
`mongodb-user list on Google Groups
<https://groups.google.com/forum/?fromgroups#!forum/mongodb-user>`_.
For confirmed issues or feature requests, open a case in
`Jira <http://jira.mongodb.org>`_ in the "MOTOR" project.

.. _Tornado: http://tornadoweb.org/

.. _asyncio: https://docs.python.org/3/library/asyncio.html

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

Contents
--------

.. toctree::
   :maxdepth: 1

   differences
   features
   installation
   requirements
   tutorial
   examples/index
   changelog
   contributors

Classes
-------

.. toctree::

   api/index

.. getting the caption italicized with a hyperlink in it requires some RST hackage

*Logo by* |musho|_

.. _musho: http://whimsyload.com

.. |musho| replace:: *Musho Rodney Alan Greenblat*
