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

# TODO: link to framework spec in dev guide.
"""asyncio compatibility layer for Motor, an asynchronous MongoDB driver."""

import asyncio
import asyncio.tasks
import functools

try:
    from asyncio import ensure_future
except ImportError:
    from asyncio import async as ensure_future


def get_event_loop():
    return asyncio.get_event_loop()


def is_event_loop(loop):
    return isinstance(loop, asyncio.AbstractEventLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError(
            "io_loop must be instance of asyncio-compatible event loop,"
            "not %r" % loop)


def get_future(loop):
    return asyncio.Future(loop=loop)


_DEFAULT = object()


def future_or_callback(future, callback, loop, return_value=_DEFAULT):
    """Compatible way to return a value in all Pythons.

    PEP 479, raise StopIteration(value) from a coroutine won't work forever,
    but "return value" doesn't work in Python 2. Instead, Motor methods that
    return values either execute a callback with the value or resolve a Future
    with it, and are implemented with callbacks rather than a coroutine
    internally.
    """
    if callback:
        raise NotImplementedError("Motor with asyncio prohibits callbacks")

    if return_value is _DEFAULT:
        return future

    chained = asyncio.Future(loop=loop)

    def done_callback(_future):
        try:
            result = _future.result()
            chained.set_result(result if return_value is _DEFAULT
                               else return_value)
        except Exception as exc:
            chained.set_exception(exc)

    future.add_done_callback(done_callback)
    return chained


def is_future(f):
    return isinstance(f, asyncio.Future)


def call_soon(loop, callback, *args, **kwargs):
    if kwargs:
        loop.call_soon(functools.partial(callback, *args, **kwargs))
    else:
        loop.call_soon(callback, *args)


coroutine = asyncio.coroutine


def pymongo_class_wrapper(f, pymongo_class):
    """Executes the coroutine f and wraps its result in a Motor class.

    See WrapAsync.
    """
    @functools.wraps(f)
    @asyncio.coroutine
    def _wrapper(self, *args, **kwargs):
        result = yield from f(self, *args, **kwargs)

        # Don't call isinstance(), not checking subclasses.
        if result.__class__ == pymongo_class:
            # Delegate to the current object to wrap the result.
            return self.wrap(result)
        else:
            return result

    return _wrapper


def yieldable(future):
    # TODO: really explain.
    return next(iter(future))
