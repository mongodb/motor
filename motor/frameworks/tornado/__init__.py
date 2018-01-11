# Copyright 2014-2016 MongoDB, Inc.
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

"""Tornado compatibility layer for Motor, an asynchronous MongoDB driver.

See "Frameworks" in the Developer Guide.
"""

import functools
import os
from concurrent.futures import ThreadPoolExecutor

import tornado.process
from tornado import concurrent, gen, ioloop

from motor.motor_common import callback_type_error

CLASS_PREFIX = ''


def get_event_loop():
    return ioloop.IOLoop.current()


def is_event_loop(loop):
    return isinstance(loop, ioloop.IOLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError(
            "io_loop must be instance of IOLoop, not %r" % loop)


def get_future(loop):
    return concurrent.Future()


if 'MOTOR_MAX_WORKERS' in os.environ:
    max_workers = int(os.environ['MOTOR_MAX_WORKERS'])
else:
    max_workers = tornado.process.cpu_count() * 5

_EXECUTOR = ThreadPoolExecutor(max_workers=max_workers)


def run_on_executor(loop, fn, *args, **kwargs):
    # Need a Tornado Future for "await" expressions. exec_fut is resolved on a
    # worker thread, loop.add_future ensures "future" is resolved on main.
    future = concurrent.Future()
    exec_fut = _EXECUTOR.submit(fn, *args, **kwargs)

    def copy(_):
        if future.done():
            return
        if exec_fut.exception() is not None:
            future.set_exception(exec_fut.exception())
        else:
            future.set_result(exec_fut.result())

    # Ensure copy runs on main thread.
    loop.add_future(exec_fut, copy)
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

        io_loop.add_future(future, done_callback)

    elif return_value is not _DEFAULT:
        chained = concurrent.Future()

        def done_callback(_future):
            try:
                _future.result()
            except Exception as exc:
                chained.set_exception(exc)
            else:
                chained.set_result(return_value)

        io_loop.add_future(future, done_callback)
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


def add_future(loop, future, callback, *args):
    loop.add_future(future, functools.partial(callback, *args))


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
