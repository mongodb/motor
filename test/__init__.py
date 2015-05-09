# Copyright 2012-2014 MongoDB, Inc.
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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import contextlib
import datetime
import functools
import gc
import logging
import os
import socket
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
from pymongo.mongo_client import _partition_node
from tornado.testing import gen_test
from tornado import gen, testing

import motor
from test.utils import one

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None


host = os.environ.get("DB_IP", "localhost")
port = int(os.environ.get("DB_PORT", 27017))
db_user = os.environ.get("DB_USER", "motor-test-root")
db_password = os.environ.get("DB_PASSWORD", "pass")

CERT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'certificates')
CLIENT_PEM = os.path.join(CERT_PATH, 'client.pem')
CA_PEM = os.path.join(CERT_PATH, 'ca.pem')


def is_server_resolvable():
    """Returns True if 'server' is resolvable."""
    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(1)
    try:
        socket.gethostbyname('server')
        return True
    except socket.error:
        return False
    finally:
        socket.setdefaulttimeout(socket_timeout)


class TestEnvironment(object):
    def __init__(self):
        self.initialized = False
        self.mongod_started_with_ssl = False
        self.mongod_validates_client_cert = False
        self.is_server_resolvable = is_server_resolvable()
        self.sync_cx = None
        self.is_mongos = False
        self.is_replica_set = False
        self.rs_name = None
        self.w = 1
        self.hosts = None
        self.arbiters = None
        self.primary = None
        self.secondaries = None
        self.v8 = False
        self.auth = False
        self.uri = None
        self.rs_uri = None

    def setup(self):
        """Called once from setup_package."""
        assert not self.initialized
        self.setup_sync_cx()
        self.setup_auth()
        self.setup_mongos()
        self.setup_rs()
        self.setup_v8()
        self.initialized = True

    def setup_sync_cx(self):
        """Get a synchronous PyMongo MongoClient and determine SSL config."""
        connectTimeoutMS = 100
        socketTimeoutMS = 30 * 1000
        try:
            self.sync_cx = pymongo.MongoClient(
                host, port,
                connectTimeoutMS=connectTimeoutMS,
                socketTimeoutMS=socketTimeoutMS,
                ssl=True)
    
            self.mongod_started_with_ssl = True
        except pymongo.errors.ConnectionFailure:
            try:
                self.sync_cx = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl_certfile=CLIENT_PEM)
    
                self.mongod_started_with_ssl = True
                self.mongod_validates_client_cert = True
            except pymongo.errors.ConnectionFailure:
                self.sync_cx = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl=False)

    def setup_auth(self):
        """Set self.auth and self.uri, and maybe create an admin user."""
        # Either we're on mongod < 2.7.1 and we can connect over localhost to
        # check if --auth is in the command line. Or we're prohibited from
        # seeing the command line so we should try blindly to create an admin
        # user.
        try:
            argv = self.sync_cx.admin.command('getCmdLineOpts')['argv']
            self.auth = ('--auth' in argv or '--keyFile' in argv)
        except pymongo.errors.OperationFailure as e:
            if e.code == 13:
                # Auth failure getting command line.
                self.auth = True
            else:
                raise
    
        if self.auth:
            self.uri = 'mongodb://%s:%s@%s:%s/admin' % (
                db_user, db_password, host, port)

            try:
                self.sync_cx.admin.add_user(db_user, db_password, roles=['root'])
            except pymongo.errors.OperationFailure:
                print("Couldn't create root user, prior test didn't clean up?")

            self.sync_cx.admin.authenticate(db_user, db_password)
    
        else:
            self.uri = 'mongodb://%s:%s/admin' % (host, port)

    def setup_mongos(self):
        """Set self.is_mongos."""
        response = self.sync_cx.admin.command('ismaster')
        self.is_mongos = response.get('msg') == 'isdbgrid'

    def setup_rs(self):
        """Determine server's replica set config."""
        response = self.sync_cx.admin.command('ismaster')
        if 'setName' in response:
            self.is_replica_set = True
            self.rs_name = str(response['setName'])
            self.rs_uri = self.uri + '?replicaSet=' + self.rs_name
            self.w = len(response['hosts'])
            self.hosts = set([_partition_node(h) for h in response["hosts"]])
            self.arbiters = set([
                _partition_node(h) for h in response.get("arbiters", [])])

            repl_set_status = self.sync_cx.admin.command('replSetGetStatus')
            primary_info = [
                m for m in repl_set_status['members']
                if m['stateStr'] == 'PRIMARY'][0]

            self.primary = _partition_node(primary_info['name'])
            self.secondaries = [
                _partition_node(m['name']) for m in repl_set_status['members']
                if m['stateStr'] == 'SECONDARY']

    def setup_v8(self):
        """Determine if server is running SpiderMonkey or V8."""
        if self.sync_cx.server_info().get('javascriptEngine') == 'V8':
            self.v8 = True


env = TestEnvironment()


def suppress_tornado_warnings():
    for name in [
            'tornado.general',
            'tornado.access']:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)


def setup_package(tornado_warnings):
    """Run once by MotorTestCase before any tests.

    If 'warn', let Tornado log warnings.
    """
    env.setup()
    if not tornado_warnings:
        suppress_tornado_warnings()


def teardown_package():
    if env.auth:
        env.sync_cx.admin.remove_user(db_user)


class MotorTestRunner(unittest.TextTestRunner):
    """Runs suite-level setup and teardown."""
    def __init__(self, *args, **kwargs):
        self.tornado_warnings = kwargs.pop('tornado_warnings', False)
        super(MotorTestRunner, self).__init__(*args, **kwargs)

    def run(self, test):
        setup_package(tornado_warnings=self.tornado_warnings)
        result = super(MotorTestRunner, self).run(test)
        teardown_package()
        return result


@contextlib.contextmanager
def assert_raises(exc_class):
    """Roughly a backport of Python 2.7's TestCase.assertRaises"""
    try:
        yield
    except exc_class:
        pass
    else:
        assert False, "%s not raised" % exc_class


class PauseMixin(object):
    @gen.coroutine
    def pause(self, seconds):
        yield gen.Task(
            self.io_loop.add_timeout, datetime.timedelta(seconds=seconds))


class MotorTest(PauseMixin, testing.AsyncTestCase):
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

    def motor_client(self, uri=None, *args, **kwargs):
        """Get a MotorClient.

        Ignores self.ssl, you must pass 'ssl' argument. You'll probably need to
        close the client to avoid file-descriptor problems after AsyncTestCase
        calls self.io_loop.close(all_fds=True).
        """
        return motor.MotorClient(
            uri or env.uri, *args, io_loop=self.io_loop, **kwargs)

    def motor_rsc(self, uri=None, *args, **kwargs):
        """Get an open MotorReplicaSetClient. Ignores self.ssl, you must pass
        'ssl' argument. You'll probably need to close the client to avoid
        file-descriptor problems after AsyncTestCase calls
        self.io_loop.close(all_fds=True).
        """
        return motor.MotorReplicaSetClient(
            uri or env.rs_uri, *args, io_loop=self.io_loop, **kwargs)

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

    @gen_test
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

    @gen_test
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
