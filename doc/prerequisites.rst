Installation Prerequisites
==========================

* `Tornado <http://www.tornadoweb.org/>`_
* `Greenlet <http://pypi.python.org/pypi/greenlet>`_
* CPython 2.5, 2.6, 2.7, or 3.2
* Although Motor works with PyPy 1.9, limitations with greenlets and PyPy's
  JIT compiler make PyPy applications that use Motor too slow for regular use
