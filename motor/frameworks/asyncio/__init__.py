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

"""asyncio compatibility layer for Motor, an asynchronous MongoDB driver.

See "Frameworks" in the Developer Guide.
"""
import asyncio
import asyncio.tasks
import functools
import multiprocessing
import os
import warnings
from asyncio import get_event_loop  # noqa: F401 - For framework interface.
from concurrent.futures import ThreadPoolExecutor

# mypy: ignore-errors

try:
    import contextvars
except ImportError:
    contextvars = None

try:
    from asyncio import coroutine
except ImportError:

    def coroutine():
        raise RuntimeError(
            "The coroutine decorator was removed in Python 3.11.  Use 'async def' instead"
        )


CLASS_PREFIX = "AsyncIO"


def is_event_loop(loop):
    return isinstance(loop, asyncio.AbstractEventLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError("io_loop must be instance of asyncio-compatible event loop, not %r" % loop)


def get_future(loop):
    return loop.create_future()


if "MOTOR_MAX_WORKERS" in os.environ:
    max_workers = int(os.environ["MOTOR_MAX_WORKERS"])
else:
    max_workers = multiprocessing.cpu_count() * 5

_EXECUTOR = ThreadPoolExecutor(max_workers=max_workers)


def _reset_global_executor():
    """Re-initialize the global ThreadPoolExecutor"""
    global _EXECUTOR  # noqa: PLW0603
    _EXECUTOR = ThreadPoolExecutor(max_workers=max_workers)


if hasattr(os, "register_at_fork"):
    # We need this to make sure that creating new clients in subprocesses doesn't deadlock.
    os.register_at_fork(after_in_child=_reset_global_executor)


def run_on_executor(loop, fn, *args, **kwargs):
    if contextvars:
        context = contextvars.copy_context()
        fn = functools.partial(context.run, fn)

    return loop.run_in_executor(_EXECUTOR, functools.partial(fn, *args, **kwargs))


# Adapted from tornado.gen.
def chain_future(a, b):
    def copy(future):
        assert future is a
        if b.done():
            return
        if a.exception() is not None:
            b.set_exception(a.exception())
        else:
            b.set_result(a.result())

    a.add_done_callback(copy)


def chain_return_value(future, loop, return_value):
    """Compatible way to return a value in all Pythons.

    PEP 479, raise StopIteration(value) from a coroutine won't work forever,
    but "return value" doesn't work in Python 2. Instead, Motor methods that
    return values resolve a Future with it, and are implemented with callbacks
    rather than a coroutine internally.
    """
    chained = loop.create_future()

    def copy(_future):
        # Return early if the task was cancelled.
        if chained.done():
            return
        if _future.exception() is not None:
            chained.set_exception(_future.exception())
        else:
            chained.set_result(return_value)

    future.add_done_callback(functools.partial(loop.call_soon_threadsafe, copy))
    return chained


def is_future(f):
    return asyncio.isfuture(f)


def call_soon(loop, callback, *args, **kwargs):
    if kwargs:
        loop.call_soon(functools.partial(callback, *args, **kwargs))
    else:
        loop.call_soon(callback, *args)


def add_future(loop, future, callback, *args):
    future.add_done_callback(functools.partial(loop.call_soon_threadsafe, callback, *args))


def pymongo_class_wrapper(f, pymongo_class):
    """Executes the coroutine f and wraps its result in a Motor class.

    See WrapAsync.
    """

    @functools.wraps(f)
    async def _wrapper(self, *args, **kwargs):
        result = await f(self, *args, **kwargs)

        # Don't call isinstance(), not checking subclasses.
        if result.__class__ == pymongo_class:
            # Delegate to the current object to wrap the result.
            return self.wrap(result)
        else:
            return result

    return _wrapper


def yieldable(future):
    warnings.warn(
        "The yieldable function is deprecated and may be removed in a future major release",
        DeprecationWarning,
        stacklevel=2,
    )
    return next(iter(future))


def platform_info():
    return "asyncio"
