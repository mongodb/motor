# Copyright 2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, unicode_literals

"""Tornado compatibility layer for MongoDB, an asynchronous MongoDB driver."""

import functools
import sys
from concurrent.futures import ThreadPoolExecutor

import tornado.process
from tornado import concurrent, gen, ioloop

from motor.motor_common import callback_type_error

DomainError = None
try:
    # If Twisted is installed. See resolve().
    from twisted.names.error import DomainError
except ImportError:
    DomainError = None


def get_event_loop():
    return ioloop.IOLoop.current()


def is_event_loop(loop):
    return isinstance(loop, ioloop.IOLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError(
            "io_loop must be instance of IOLoop, not %r" % loop)


# Beginning in Tornado 4, TracebackFuture is a deprecated alias for Future.
# Future-proof Motor in case TracebackFuture is some day removed. Remove this
# Future-proofing once we drop support for Tornado 3.
try:
    _TornadoFuture = concurrent.TracebackFuture
except AttributeError:
    _TornadoFuture = concurrent.Future


def get_future(loop):
    return _TornadoFuture()


if sys.version_info >= (3, 5):
    # Python 3.5+ sets max_workers=(cpu_count * 5) automatically.
    _EXECUTOR = ThreadPoolExecutor()
else:
    _EXECUTOR = ThreadPoolExecutor(max_workers=tornado.process.cpu_count() * 5)


def run_on_executor(fn, self, *args, **kwargs):
    # Need a Tornado Future for "await" expressions.
    future = _TornadoFuture()
    gen.chain_future(_EXECUTOR.submit(fn, self, *args, **kwargs), future)
    return future

_DEFAULT = object()


def future_or_callback(future, callback, io_loop, return_value=_DEFAULT):
    """Compatible way to return a value in all Pythons.

    PEP 479, raise StopIteration(value) from a coroutine won't work forever,
    but "return value" doesn't work in Python 2. Instead, Motor methods that
    return values either execute a callback with the value or resolve a Future
    with it, and are implemented with callbacks rather than a coroutine
    internally.
    """
    if callback:
        if not callable(callback):
            raise callback_type_error

        # Motor's callback convention is "callback(result, error)".
        def done_callback(_future):
            try:
                result = _future.result()
                callback(result if return_value is _DEFAULT else return_value,
                         None)
            except Exception as exc:
                callback(None, exc)

        future.add_done_callback(done_callback)

    elif return_value is not _DEFAULT:
        chained = _TornadoFuture()

        def done_callback(_future):
            try:
                result = _future.result()
                chained.set_result(result if return_value is _DEFAULT
                                   else return_value)
            except Exception as exc:
                # TODO: exc_info
                chained.set_exception(exc)

        future.add_done_callback(done_callback)
        return chained

    else:
        return future


def is_future(f):
    return isinstance(f, concurrent.Future)


def call_soon(loop, callback, *args, **kwargs):
    if args or kwargs:
        loop.add_callback(functools.partial(callback, *args, **kwargs))
    else:
        loop.add_callback(callback)


def coroutine(f):
    """A coroutine that accepts an optional callback.

    Given a callback, the function returns None, and the callback is run
    with (result, error). Without a callback the function returns a Future.
    """
    coro = gen.coroutine(f)

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        callback = kwargs.pop('callback', None)
        if callback and not callable(callback):
            raise callback_type_error
        future = coro(*args, **kwargs)
        if callback:
            def _callback(_future):
                try:
                    result = _future.result()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
            future.add_done_callback(_callback)
        else:
            return future
    return wrapper


def pymongo_class_wrapper(f, pymongo_class):
    """Executes the coroutine f and wraps its result in a Motor class.

    See WrapAsync.
    """
    @functools.wraps(f)
    @coroutine
    def _wrapper(self, *args, **kwargs):
        result = yield f(self, *args, **kwargs)

        # Don't call isinstance(), not checking subclasses.
        if result.__class__ == pymongo_class:
            # Delegate to the current object to wrap the result.
            raise gen.Return(self.wrap(result))
        else:
            raise gen.Return(result)

    return _wrapper


def yieldable(future):
    # TODO: really explain.
    return future
