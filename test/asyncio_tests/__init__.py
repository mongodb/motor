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
import gc
import inspect
import os
import time
import unittest
from unittest import SkipTest
from concurrent.futures import ThreadPoolExecutor

import pymongo.errors

from motor import motor_asyncio
from test.version import _parse_version_string, padded
from test.test_environment import env, CLIENT_PEM


class _TestMethodWrapper(object):
    """Wraps a test method to raise an error if it returns a value.

    This is mainly used to detect undecorated generators (if a test
    method yields it must use a decorator to consume the generator),
    but will also detect other kinds of return values (these are not
    necessarily errors, but we alert anyway since there is no good
    reason to return a value from a test).

    Adapted from Tornado's test framework.
    """
    def __init__(self, orig_method):
        self.orig_method = orig_method

    def __call__(self):
        result = self.orig_method()
        if inspect.isgenerator(result):
            raise TypeError("Generator test methods should be decorated with "
                            "@asyncio_test")
        elif result is not None:
            raise ValueError("Return value from test method ignored: %r" %
                             result)

    def __getattr__(self, name):
        """Proxy all unknown attributes to the original method.

        This is important for some of the decorators in the `unittest`
        module, such as `unittest.skipIf`.
        """
        return getattr(self.orig_method, name)


class AsyncIOTestCase(unittest.TestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)

        # It's easy to forget the @asyncio_test decorator, but if you do
        # the test will silently be ignored because nothing will consume
        # the generator. Replace the test method with a wrapper that will
        # make sure it's not an undecorated generator.
        # (Adapted from Tornado's AsyncTestCase.)
        setattr(self, methodName, _TestMethodWrapper(
            getattr(self, methodName)))

    def setUp(self):
        super(AsyncIOTestCase, self).setUp()

        # Ensure that the event loop is passed explicitly in Motor.
        asyncio.set_event_loop(None)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.loop = asyncio.new_event_loop()
        self.loop.set_default_executor(self.executor)

        if self.ssl and not env.mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        self.cx = self.asyncio_client()
        self.db = self.cx.motor_test
        self.collection = self.db.test_collection
        self.loop.run_until_complete(self.collection.drop())

    def get_client_kwargs(self, **kwargs):
        if env.mongod_validates_client_cert:
            kwargs.setdefault('ssl_certfile', CLIENT_PEM)

        kwargs.setdefault('ssl', env.mongod_started_with_ssl)
        kwargs.setdefault('io_loop', self.loop)

        return kwargs

    def asyncio_client(self, uri=None, *args, **kwargs):
        """Get an AsyncIOMotorClient.

        Ignores self.ssl, you must pass 'ssl' argument.
        """
        return motor_asyncio.AsyncIOMotorClient(
            uri or env.uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    def asyncio_rsc(self, uri=None, *args, **kwargs):
        """Get an AsyncIOMotorReplicaSetClient.

        Ignores self.ssl, you must pass 'ssl' argument.
        """
        return motor_asyncio.AsyncIOMotorReplicaSetClient(
            uri or env.rs_uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    @asyncio.coroutine
    def make_test_data(self):
        yield from self.collection.remove()
        yield from self.collection.insert([{'_id': i} for i in range(200)])

    @asyncio.coroutine
    def wait_for_cursor(self, collection, cursor_id, retrieved):
        """Ensure a cursor opened during the test is closed on the
        server, e.g. after dereferencing an open cursor on the client.
        """
        patience_seconds = 20
        start = time.time()
        collection_name = collection.name
        db_name = collection.database.name
        sync_collection = env.sync_cx[db_name][collection_name]
        while True:
            sync_cursor = sync_collection.find().batch_size(1)
            sync_cursor._Cursor__id = cursor_id
            sync_cursor._Cursor__retrieved = retrieved

            try:
                next(sync_cursor)
                if not sync_cursor.cursor_id:
                    # We exhausted the result set before cursor was killed.
                    self.fail("Cursor finished before killed")
            except pymongo.errors.CursorNotFound:
                # Success!
                return
            finally:
                # Avoid spurious errors trying to close this cursor.
                sync_cursor._Cursor__id = None

            retrieved = sync_cursor._Cursor__retrieved
            now = time.time()
            if now - start > patience_seconds:
                self.fail("Cursor not closed")
            else:
                # Let the loop run, might be working on closing the cursor.
                yield from asyncio.sleep(0.25, loop=self.loop)

    make_test_data.__test__ = False

    def tearDown(self):
        self.cx.close()
        self.executor.shutdown()
        self.loop.stop()
        self.loop.run_forever()
        self.loop.close()
        gc.collect()


def get_async_test_timeout(default=5):
    """Get the global timeout setting for async tests.

    Returns a float, the timeout in seconds.
    """
    try:
        timeout = float(os.environ.get('ASYNC_TEST_TIMEOUT'))
        return max(timeout, default)
    except (ValueError, TypeError):
        return default


# TODO: Spin off to a PyPI package.
def asyncio_test(func=None, timeout=None):
    """Decorator for coroutine methods of AsyncIOTestCase::

        class MyTestCase(AsyncIOTestCase):
            @asyncio_test
            def test(self):
                # Your test code here....
                pass

    Default timeout is 5 seconds. Override like::

        class MyTestCase(AsyncIOTestCase):
            @asyncio_test(timeout=10)
            def test(self):
                # Your test code here....
                pass

    You can also set the ASYNC_TEST_TIMEOUT environment variable to a number
    of seconds. The final timeout is the ASYNC_TEST_TIMEOUT or the timeout
    in the test (5 seconds or the passed-in timeout), whichever is longest.
    """
    def wrap(f):
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            if timeout is None:
                actual_timeout = get_async_test_timeout()
            else:
                actual_timeout = get_async_test_timeout(timeout)

            coro_exc = None

            def exc_handler(loop, context):
                nonlocal coro_exc
                coro_exc = context['exception']

                # Raise CancelledError from run_until_complete below.
                task.cancel()

            self.loop.set_exception_handler(exc_handler)
            coro = asyncio.coroutine(f)(self, *args, **kwargs)
            coro = asyncio.wait_for(coro, actual_timeout, loop=self.loop)
            task = asyncio.async(coro, loop=self.loop)
            try:
                self.loop.run_until_complete(task)
            except:
                if coro_exc:
                    # Raise the error thrown in on_timeout, with only the
                    # traceback from the coroutine itself, not from
                    # run_until_complete.
                    raise coro_exc from None

                raise

        return wrapped

    if func is not None:
        # Used like:
        #     @gen_test
        #     def f(self):
        #         pass
        if not inspect.isfunction(func):
            msg = ("%r is not a test method. Pass a timeout as"
                   " a keyword argument, like @asyncio_test(timeout=7)")
            raise TypeError(msg % func)
        return wrap(func)
    else:
        # Used like @gen_test(timeout=10)
        return wrap


@asyncio.coroutine
def get_command_line(client):
    command_line = yield from client.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    return command_line


@asyncio.coroutine
def server_is_mongos(client):
    ismaster_response = yield from client.admin.command('ismaster')
    return ismaster_response.get('msg') == 'isdbgrid'


@asyncio.coroutine
def version(client):
    info = yield from client.server_info()
    return _parse_version_string(info["version"])


@asyncio.coroutine
def at_least(client, min_version):
    client_version = yield from version(client)
    return client_version >= tuple(padded(min_version, 4))


@asyncio.coroutine
def skip_if_mongos(client):
    is_mongos = yield from server_is_mongos(client)
    if is_mongos:
        raise unittest.SkipTest("connected to mongos")


@asyncio.coroutine
def remove_all_users(db):
    version_check = yield from at_least(db.connection, (2, 5, 4))
    if version_check:
        yield from db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield from db.system.users.remove({})
