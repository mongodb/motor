DNS Configuration
=================

Motor uses Tornado's DNS :class:`~tornado.netutil.Resolver` API. By default
Tornado uses a blocking resolver, but you can override this configuration at
application startup time. For example, to use the asynchronous C-ARES resolver
with pycares_ installed::

    from tornado.netutil import Resolver

    Resolver.configure('tornado.platform.caresresolver.CaresResolver')

.. _pycares: https://pypi.python.org/pypi/pycares
