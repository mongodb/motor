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

"""Utilities for testing Motor with asyncio."""

import asyncio
import functools
import inspect
import os
import unittest
from asyncio import events, tasks

from motor import motor_asyncio


class AsyncIOTestCase(unittest.TestCase):
    def setUp(self):
        # Ensure that the event loop is passed explicitly in Motor.
        events.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

    def asyncio_client(self, uri=None, *args, **kwargs):
        """Get an AsyncIOMotorClient.

        Ignores self.ssl, you must pass 'ssl' argument.
        """
        return motor_asyncio.AsyncIOMotorClient(
            uri or 'mongodb://localhost', *args, io_loop=self.loop, **kwargs)

    def tearDown(self):
        self.loop.close()


def get_async_test_timeout():
    """Get the global timeout setting for async tests.

    Returns a float, the timeout in seconds.
    """
    try:
        return float(os.environ.get('ASYNC_TEST_TIMEOUT'))
    except (ValueError, TypeError):
        return 5


# TODO: doc. Spin off to a PyPI package.
def asyncio_test(func=None, timeout=None):
    """Decorator like Tornado's gen_test."""
    if timeout is None:
        timeout = get_async_test_timeout()

    def wrap(f):
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            def on_timeout():
                if inspect.isgenerator(coro):
                    # Simply doing task.cancel() raises an unhelpful traceback.
                    # We want to include the coroutine's stack, so throw into
                    # the generator and record its traceback in exc_handler().
                    msg = 'timed out after %s seconds' % timeout
                    coro.throw(asyncio.CancelledError(msg))

            coro_exc = None

            def exc_handler(loop, context):
                nonlocal coro_exc
                coro_exc = context['exception']

                # Raise CancelledError from run_until_complete below.
                task.cancel()

            self.loop.set_exception_handler(exc_handler)
            coro = asyncio.coroutine(f)(self, *args, **kwargs)
            timeout_handle = self.loop.call_later(timeout, on_timeout)
            task = tasks.Task(coro, loop=self.loop)
            try:
                self.loop.run_until_complete(task)
            except:
                if coro_exc:
                    # Raise the error thrown in on_timeout, with only the
                    # traceback from the coroutine itself, not from
                    # run_until_complete.
                    raise coro_exc from None

                raise

            # self.loop.run_until_complete(coro)
            timeout_handle.cancel()

        return wrapped

    if func is not None:
        # Used like:
        #     @gen_test
        #     def f(self):
        #         pass
        return wrap(func)
    else:
        # Used like @gen_test(timeout=10)
        return wrap
