Motor: Asynchronous Python driver for MongoDB
=============================================

.. image:: _static/motor.png
    :align: center

About
-----

Motor presents a coroutine-based API for non-blocking access to
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

Getting Help
------------
If you're having trouble or have questions about Motor, ask your question on
our `MongoDB Community Forum <https://developer.mongodb.com/community/forums/tags/c/drivers-odms-connectors/7/motor-driver>`_.
You may also want to consider a
`commercial support subscription <https://support.mongodb.com/welcome>`_.
Once you get an answer, it'd be great if you could work it back into this
documentation and contribute!

Issues
------
All issues should be reported (and can be tracked / voted for /
commented on) at the main `MongoDB JIRA bug tracker
<http://jira.mongodb.org/browse/MOTOR>`_, in the "Motor"
project.

Feature Requests / Feedback
---------------------------
Use our `feedback engine <https://feedback.mongodb.com/forums/924286-drivers>`_
to send us feature requests and general feedback about PyMongo.

Contributing
------------
**Motor** has a large :doc:`community <contributors>` and
contributions are always encouraged. Contributions can be as simple as
minor tweaks to this documentation. To contribute, fork the project on
`GitHub <http://github.com/mongodb/motor/>`_ and send a
pull request.

Changes
-------
See the :doc:`changelog` for a full list of changes to Motor.

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
   migrate-to-motor-2
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
