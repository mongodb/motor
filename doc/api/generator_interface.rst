.. _generator-interface:

Generator Interface
===================

.. currentmodule:: motor

Motor provides yield points to be used with `tornado.gen
<http://www.tornadoweb.org/documentation/gen.html>`_,
within functions or methods decorated by ``@gen.engine``. See
:ref:`generator-interface-example`.

.. autoclass:: Op
      :members:

.. autoclass:: WaitOp
      :members:

.. autoclass:: WaitAllOps
      :members:
