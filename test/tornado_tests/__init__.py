# Copyright 2012-2015 MongoDB, Inc.
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

from __future__ import unicode_literals

"""Utilities for testing Motor with Tornado."""

import concurrent.futures
import datetime
import functools
import gc
import logging
import time

try:
    # Python 2.6.
    from unittest2 import SkipTest
    import unittest2 as unittest
except ImportError:
    from unittest import SkipTest  # If this fails you need unittest2.
    import unittest

import pymongo
import pymongo.errors
from bson import SON
from mockupdb import MockupDB
from tornado import gen, testing

import motor
from test.test_environment import env, CLIENT_PEM
from test.assert_logs_backport import AssertLogsMixin
from test.utils import one
from test.version import padded, _parse_version_string


def suppress_tornado_warnings():
    for name in [
            'tornado.general',
            'tornado.access']:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)


@gen.coroutine
def version(client):
    info = yield client.server_info()
    raise gen.Return(_parse_version_string(info["version"]))


@gen.coroutine
def at_least(client, min_version):
    client_version = yield version(client)
    raise gen.Return(client_version >= tuple(padded(min_version, 4)))


@gen.coroutine
def get_command_line(client):
    command_line = yield client.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    raise gen.Return(command_line)


@gen.coroutine
def server_is_mongos(client):
    ismaster_response = yield client.admin.command('ismaster')
    raise gen.Return(ismaster_response.get('msg') == 'isdbgrid')


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    version_check = yield at_least(db.connection, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    version_check = yield at_least(db.connection, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})


class PauseMixin(object):
    @gen.coroutine
    def pause(self, seconds):
        yield gen.Task(
            self.io_loop.add_timeout, datetime.timedelta(seconds=seconds))


class MotorTest(PauseMixin, AssertLogsMixin, testing.AsyncTestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super(MotorTest, self).setUp()

        if self.ssl and not env.mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        if env.auth:
            self.cx = self.motor_client(env.uri, ssl=self.ssl)
        else:
            self.cx = self.motor_client(ssl=self.ssl)

        self.db = self.cx.motor_test
        self.collection = self.db.test_collection

    @gen.coroutine
    def make_test_data(self):
        yield self.collection.remove()
        yield self.collection.insert([{'_id': i} for i in range(200)])

    make_test_data.__test__ = False

    @gen.coroutine
    def wait_for_cursor(self, collection, cursor_id, retrieved):
        """Ensure a cursor opened during the test is closed on the
        server, e.g. after dereferencing an open cursor on the client:

            collection = self.cx.motor_test.test_collection
            cursor = collection.find()

            # Open it server-side
            yield cursor.fetch_next
            cursor_id = cursor.cursor_id
            retrieved = cursor.delegate._Cursor__retrieved

            # Clear cursor reference from this scope and from Runner
            del cursor
            yield gen.Task(self.io_loop.add_callback)

            # Wait for cursor to be closed server-side
            yield self.wait_for_cursor(collection, cursor_id, retrieved)

        `yield cursor.close()` is usually simpler.
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
            except pymongo.errors.OperationFailure as exc:
                if exc.code == 16336:
                    # mongos 2.2 "cursor not found" error, success!
                    return
                raise
            finally:
                # Avoid spurious errors trying to close this cursor.
                sync_cursor._Cursor__id = None

            retrieved = sync_cursor._Cursor__retrieved
            now = time.time()
            if now - start > patience_seconds:
                self.fail("Cursor not closed")
            else:
                # Let the loop run, might be working on closing the cursor
                yield self.pause(0.1)
                gc.collect()

    def get_client_kwargs(self, **kwargs):
        kwargs.setdefault('io_loop', self.io_loop)
        ssl = env.mongod_started_with_ssl
        kwargs.setdefault('ssl', ssl)
        if kwargs['ssl'] and env.mongod_validates_client_cert:
            kwargs.setdefault('ssl_certfile', CLIENT_PEM)

        return kwargs

    def motor_client(self, uri=None, *args, **kwargs):
        """Get a MotorClient.

        Ignores self.ssl, you must pass 'ssl' argument. You'll probably need to
        close the client to avoid file-descriptor problems after AsyncTestCase
        calls self.io_loop.close(all_fds=True).
        """
        return motor.MotorClient(
            uri or env.uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    def motor_rsc(self, uri=None, *args, **kwargs):
        """Get an open MotorReplicaSetClient. Ignores self.ssl, you must pass
        'ssl' argument. You'll probably need to close the client to avoid
        file-descriptor problems after AsyncTestCase calls
        self.io_loop.close(all_fds=True).
        """
        return motor.MotorReplicaSetClient(
            uri or env.rs_uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    @gen.coroutine
    def check_optional_callback(self, fn, *args, **kwargs):
        """Take a function and verify that it accepts a 'callback' parameter
        and properly type-checks it. If 'required', check that fn requires
        a callback.

        NOTE: This method can call fn several times, so it should be relatively
        free of side-effects. Otherwise you should test fn without this method.

        :Parameters:
          - `fn`: A function that accepts a callback
          - `required`: Whether `fn` should require a callback or not
          - `callback`: To be called with ``(None, error)`` when done
        """
        partial_fn = functools.partial(fn, *args, **kwargs)
        self.assertRaises(TypeError, partial_fn, callback='foo')
        self.assertRaises(TypeError, partial_fn, callback=1)

        # Should not raise
        yield partial_fn(callback=None)

        # Should not raise
        (result, error), _ = yield gen.Task(partial_fn)
        if error:
            raise error

    def tearDown(self):
        env.sync_cx.motor_test.test_collection.remove()
        self.cx.close()
        super(MotorTest, self).tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
        if not env.is_replica_set:
            raise SkipTest("Not connected to a replica set")

        self.rsc = self.motor_rsc()
        self.rsc = self.motor_rsc()


class MotorMockServerTest(MotorTest):

    executor = concurrent.futures.ThreadPoolExecutor(1)

    def client_and_mock_server(self, *args, **kwargs):
        server = MockupDB(*args, **kwargs)
        server.run()
        self.addCleanup(server.stop)

        client = motor.motor_tornado.MotorClient(server.uri,
                                                 io_loop=self.io_loop)

        return client, server

    def run_thread(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)


class _TestExhaustCursorMixin(object):
    """Test that clients properly handle errors from exhaust cursors.

    Inherit from this class and from MotorTest, and override
    _get_client(self, **kwargs).
    """
    def setUp(self):
        super(_TestExhaustCursorMixin, self).setUp()
        if env.is_mongos:
            raise SkipTest("mongos doesn't support exhaust cursors")

    def tearDown(self):
        env.sync_cx.motor_test.test.remove(w=env.w)
        super(_TestExhaustCursorMixin, self).tearDown()

    @testing.gen_test
    def test_exhaust_query_server_error(self):
        # When doing an exhaust query, the socket stays checked out on success
        # but must be checked in on error to avoid counter leak.
        client = yield self._get_client(max_pool_size=1).open()
        collection = client.motor_test.test
        pool = client._get_primary_pool()
        sock_info = one(pool.sockets)

        # This will cause OperationFailure in all mongo versions since
        # the value for $orderby must be a document.
        cursor = collection.find(
            SON([('$query', {}), ('$orderby', True)]), exhaust=True)

        with self.assertRaises(pymongo.errors.OperationFailure):
            yield cursor.fetch_next

        self.assertFalse(sock_info.closed)
        self.assertEqual(sock_info, one(pool.sockets))

    @testing.gen_test
    def test_exhaust_query_network_error(self):
        # When doing an exhaust query, the socket stays checked out on success
        # but must be checked in on error to avoid counter leak.
        client = yield self._get_client(max_pool_size=1).open()
        collection = client.motor_test.test
        pool = client._get_primary_pool()
        pool._check_interval_seconds = None  # Never check.

        # Cause a network error.
        sock_info = one(pool.sockets)
        sock_info.sock.close()
        cursor = collection.find(exhaust=True)
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield cursor.fetch_next

        self.assertTrue(sock_info.closed)
        del cursor
        self.assertNotIn(sock_info, pool.sockets)
