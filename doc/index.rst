Motor: Asynchronous Python driver for MongoDB
=============================================

.. image:: _static/motor.png
    :align: center

About
-----

Motor presents a callback- or Future-based API for non-blocking access to
MongoDB from Tornado_ or asyncio_.

The `source is on GitHub <https://github.com/mongodb/motor>`_ and
the docs are on `ReadTheDocs <https://motor.readthedocs.io/>`_.

    "We use Motor in high throughput environments, processing tens of thousands
    of requests per second. It allows us to take full advantage of modern
    hardware, ensuring we utilise the entire capacity of our purchased CPUs.
    This helps us be more efficient with computing power, compute spend and
    minimises the environmental impact of our infrastructure as a result."

    --*David Mytton, Server Density*

    "We develop easy-to-use sensors and sensor systems with open source
    software to ensure every innovator, from school child to laboratory
    researcher, has the same opportunity to create. We integrate Motor into our
    software to guarantee massively scalable sensor systems for everyone."

    --*Ryan Smith, inXus Interactive*

Install with::

    $ python -m pip install motor

.. _Tornado: http://tornadoweb.org/

.. _asyncio: https://docs.python.org/3/library/asyncio.html

.. _PyMongo: http://pypi.python.org/pypi/pymongo/

How To Ask For Help
-------------------

Post questions about Motor to the
`mongodb-user list on Google Groups
<https://groups.google.com/forum/?fromgroups#!forum/mongodb-user>`_.
For confirmed issues or feature requests, open a case in
`Jira <http://jira.mongodb.org>`_ in the "MOTOR" project.

Contents
--------

.. toctree::
   :maxdepth: 1

   differences
   features
   installation
   requirements
   configuration
   tutorial-tornado
   tutorial-asyncio
   examples/index
   changelog
   migrate-to-motor-1
   developer-guide
   contributors

Classes
-------

.. toctree::

   api-tornado/index
   api-asyncio/index

.. getting the caption italicized with a hyperlink in it requires some RST hackage

*Logo by* |musho|_

.. _musho: http://whimsyload.com

.. |musho| replace:: *Musho Rodney Alan Greenblat*
