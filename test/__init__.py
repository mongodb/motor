# Copyright 2012 10gen, Inc.
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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""
import contextlib

import datetime
import functools
import os
import sys
import time

import pymongo
import pymongo.errors
from nose.plugins.skip import SkipTest
from pymongo.mongo_client import _partition_node
from tornado import gen, testing

import motor

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None


host = os.environ.get("DB_IP", "localhost")
port = int(os.environ.get("DB_PORT", 27017))


@contextlib.contextmanager
def assert_raises(exc_class):
    """Roughly a backport of Python 2.7's TestCase.assertRaises"""
    try:
        yield
    except exc_class:
        pass
    else:
        assert False, "%s not raised" % exc_class


class AssertEqual(gen.Task):
    def __init__(self, expected, func, *args, **kwargs):
        super(AssertEqual, self).__init__(func, *args, **kwargs)
        self.expected = expected

    def get_result(self):
        (result, error), _ = self.runner.pop_result(self.key)
        if error:
            raise error

        if self.expected != result:
            raise AssertionError("%s returned %s\nnot\n%s" % (
                self.func, repr(result), repr(self.expected)))

        return result


class AssertTrue(AssertEqual):
    def __init__(self, func, *args, **kwargs):
        super(AssertTrue, self).__init__(True, func, *args, **kwargs)


class AssertFalse(AssertEqual):
    def __init__(self, func, *args, **kwargs):
        super(AssertFalse, self).__init__(False, func, *args, **kwargs)


class MotorTest(testing.AsyncTestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super(MotorTest, self).setUp()

        # Store a regular synchronous pymongo MongoClient for convenience while
        # testing. Set a timeout so we don't hang a test because, say, Mongo
        # isn't up or is hung by a long-running $where clause.
        connectTimeoutMS = socketTimeoutMS = 30 * 1000
        if self.ssl:
            if not HAVE_SSL:
                raise SkipTest("Python compiled without SSL")
            try:
                self.sync_cx = pymongo.MongoClient(
                    host, port, connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl=True)
            except pymongo.errors.ConnectionFailure:
                raise SkipTest("mongod doesn't support SSL, or is down")
        else:
            self.sync_cx = pymongo.MongoClient(
                host, port, connectTimeoutMS=connectTimeoutMS,
                socketTimeoutMS=socketTimeoutMS,
                ssl=False)

        self.is_replica_set = False
        response = self.sync_cx.admin.command('ismaster')
        if 'setName' in response:
            self.is_replica_set = True
            self.name = str(response['setName'])
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
            
        self.sync_db = self.sync_cx.pymongo_test
        self.sync_coll = self.sync_db.test_collection
        self.sync_coll.drop()

        # Make some test data
        self.sync_coll.ensure_index([('s', pymongo.ASCENDING)], unique=True)
        self.sync_coll.insert(
            [{'_id': i, 's': hex(i)} for i in range(200)])

        self.cx = self.motor_client_sync()

    @gen.coroutine
    def wait_for_cursor(self, collection, cursor_id):
        """Ensure a cursor opened during the test is closed on the
        server, e.g. after dereferencing an open cursor on the client:

            cursor = self.cx.pymongo_test.test_collection.find()

            # Open it server-side
            yield cursor.fetch_next
            cursor_id = cursor.cursor_id

            # Clear cursor reference from this scope and from Runner
            del cursor
            yield gen.Task(self.io_loop.add_callback)

            # Wait for cursor to be closed server-side
            yield self.wait_for_cursor(clone)

        `yield motor.Op(cursor.close)` is usually simpler.
        """
        patience_seconds = 20
        start = self.io_loop.time()

        cursor = collection.find()
        cursor.delegate._Cursor__id = cursor_id

        while True:
            try:
                yield cursor.fetch_next
            except pymongo.errors.OperationFailure, e:
                # Let's check this error was because the cursor was killed,
                # not a test bug. mongod reports "cursor id 'N' not valid at
                # server", mongos says:
                # "database error: could not find cursor in cache for id N
                # over collection pymongo_test.test_collection".
                self.assertTrue(
                    "not valid at server" in e.args[0] or
                    "could not find cursor in cache" in e.args[0])

                # Success; avoid spurious errors trying to close after loop is
                # closed.
                cursor.delegate._Cursor__id = None
                return
            else:
                now = self.io_loop.time()
                if now - start > patience_seconds:
                    self.fail("Cursor not closed")
                else:
                    yield gen.Task(
                        self.io_loop.add_timeout,
                        datetime.timedelta(seconds=0.1))

    @gen.coroutine
    def motor_client(self, host=host, port=port, *args, **kwargs):
        """Get an open MotorClient. Ignores self.ssl, you must pass 'ssl'
        argument. You'll probably need to close the client to avoid
        file-descriptor problems after AsyncTestCase calls
        self.io_loop.close(all_fds=True).
        """
        client = motor.MotorClient(
            host, port, *args, io_loop=self.io_loop, **kwargs)

        yield motor.Op(client.open)
        raise gen.Return(client)

    def motor_client_sync(self, host=host, port=port, *args, **kwargs):
        """Get an open MotorClient. Ignores self.ssl, you must pass 'ssl'
        argument.
        """
        return self.io_loop.run_sync(functools.partial(
            self.motor_client, host, port, *args, **kwargs))

    @gen.coroutine
    def check_callback_handling(self, fn, required):
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
        self.assertRaises(TypeError, fn, callback='foo')
        self.assertRaises(TypeError, fn, callback=1)

        if required:
            self.assertRaises(TypeError, fn)
            self.assertRaises(TypeError, fn, None)
        else:
            # Should not raise
            fn(callback=None)

        # Should not raise
        yield motor.Op(fn)

    @gen.coroutine
    def check_required_callback(self, fn, *args, **kwargs):
        yield self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), True)

    @gen.coroutine
    def check_optional_callback(self, fn, *args, **kwargs):
        yield self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), False)

    def tearDown(self):
        self.sync_coll.drop()
        self.cx.close()
        super(MotorTest, self).tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
        if not self.is_replica_set:
            raise SkipTest("Not connected to a replica set")

        self.rsc = self.motor_rsc_sync()

    @gen.coroutine
    def motor_rsc(self, host=host, port=port, *args, **kwargs):
        """Get an open MotorReplicaSetClient. Ignores self.ssl, you must pass
        'ssl' argument. You'll probably need to close the client to avoid
        file-descriptor problems after AsyncTestCase calls
        self.io_loop.close(all_fds=True).
        """
        client = motor.MotorReplicaSetClient(
            '%s:%s' % (host, port), *args, io_loop=self.io_loop,
            replicaSet=self.name, **kwargs)

        yield motor.Op(client.open)
        raise gen.Return(client)

    def motor_rsc_sync(self, host=host, port=port, *args, **kwargs):
        """Get an open MotorClient. Ignores self.ssl, you must pass 'ssl'
        argument.
        """
        return self.io_loop.run_sync(functools.partial(
            self.motor_rsc, host, port, *args, **kwargs))

    def tearDown(self):
        self.rsc.close()
        super(MotorReplicaSetTestBase, self).tearDown()
