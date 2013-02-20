Motor: Asynchronous Python driver for Tornado and MongoDB
=========================================================

.. image:: _static/motor.png
    :align: center

.. getting the caption italicized with a hyperlink in it requires some RST hackage

*Logo by* |musho|_

.. _musho: http://whimsyload.com

.. |musho| replace:: *Musho Rodney Alan Greenblat*

Motor wraps PyMongo_ and presents a Tornado_ callback-based API for
non-blocking access to MongoDB.

**Author**: A. Jesse Jiryu Davis

    "Motor uses a clever greenlet-based approach to fully support both
    synchronous and asynchronous interfaces from a single codebase. It's great
    to see companies like 10gen produce first-party asynchronous drivers for
    their products."

    --*Ben Darnell, Tornado maintainer*

.. _Tornado: http://tornadoweb.org/

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

.. toctree::
   :maxdepth: 1

   differences
   features
   installation
   tutorial
   examples/index
   changelog
   contributors

Classes
-------

.. toctree::

   api/index
