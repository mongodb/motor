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

mongod_started_with_ssl = False
sync_cx = None
sync_db = None
sync_coll = None


def setup_package():
    global mongod_started_with_ssl
    global sync_cx
    global sync_db
    global sync_coll

    connectTimeoutMS = socketTimeoutMS = 30 * 1000

    # Store a regular synchronous pymongo MongoClient for convenience while
    # testing. Try over SSL first.
    try:
        sync_cx = pymongo.MongoClient(
            host, port,
            connectTimeoutMS=connectTimeoutMS,
            socketTimeoutMS=socketTimeoutMS,
            ssl=True)

        mongod_started_with_ssl = True
    except pymongo.errors.ConnectionFailure:
        sync_cx = pymongo.MongoClient(
            host, port,
            connectTimeoutMS=connectTimeoutMS,
            socketTimeoutMS=socketTimeoutMS,
            ssl=False)

    sync_db = sync_cx.pymongo_test
    sync_coll = sync_db.test_collection


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

        if self.ssl and not mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        self.is_replica_set = False
        response = sync_cx.admin.command('ismaster')
        if 'setName' in response:
            self.is_replica_set = True
            self.name = str(response['setName'])
            self.w = len(response['hosts'])
            self.hosts = set([_partition_node(h) for h in response["hosts"]])
            self.arbiters = set([
                _partition_node(h) for h in response.get("arbiters", [])])

            repl_set_status = sync_cx.admin.command('replSetGetStatus')
            primary_info = [
                m for m in repl_set_status['members']
                if m['stateStr'] == 'PRIMARY'][0]

            self.primary = _partition_node(primary_info['name'])
            self.secondaries = [
                _partition_node(m['name']) for m in repl_set_status['members']
                if m['stateStr'] == 'SECONDARY']
            
        sync_coll.drop()

        # Make some test data
        sync_coll.ensure_index([('s', pymongo.ASCENDING)], unique=True)
        sync_coll.insert(
            [{'_id': i, 's': hex(i)} for i in range(200)])

        self.cx = self.motor_client()

    @gen.coroutine
    def wait_for_cursor(self, collection, cursor_id, retrieved):
        """Ensure a cursor opened during the test is closed on the
        server, e.g. after dereferencing an open cursor on the client:

            collection = self.cx.pymongo_test.test_collection
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
        sync_collection = sync_cx[db_name][collection_name]
        while True:
            sync_cursor = sync_collection.find()
            sync_cursor._Cursor__id = cursor_id
            sync_cursor._Cursor__retrieved = retrieved

            try:
                next(sync_cursor)
            except pymongo.errors.OperationFailure, e:
                # Let's check this error was because the cursor was killed,
                # not a test bug. mongod reports "cursor id 'N' not valid at
                # server", mongos says:
                # "database error: could not find cursor in cache for id N
                # over collection pymongo_test.test_collection".
                self.assertTrue(
                    "not valid at server" in e.args[0] or
                    "could not find cursor in cache" in e.args[0])

                # Success!
                return
            finally:
                # Avoid spurious errors trying to close this cursor.
                sync_cursor._Cursor__id = None

            now = time.time()
            if now - start > patience_seconds:
                self.fail("Cursor not closed")
            else:
                # Let the loop run, might be working on closing the cursor
                yield self.pause(0.1)

    def motor_client(self, host=host, port=port, *args, **kwargs):
        """Get a MotorClient.

        Ignores self.ssl, you must pass 'ssl' argument. You'll probably need to
        close the client to avoid file-descriptor problems after AsyncTestCase
        calls self.io_loop.close(all_fds=True).
        """
        return motor.MotorClient(
            host, port, *args, io_loop=self.io_loop, **kwargs)

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
            self.assertRaises(TypeError, fn, callback=None)
        else:
            # Should not raise
            yield fn(callback=None)

        # Should not raise
        (result, error), _ = yield gen.Task(fn)
        if error:
            raise error

    @gen.coroutine
    def check_required_callback(self, fn, *args, **kwargs):
        yield self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), True)

    @gen.coroutine
    def check_optional_callback(self, fn, *args, **kwargs):
        yield self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), False)

    def tearDown(self):
        sync_coll.drop()
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

        yield client.open()
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
