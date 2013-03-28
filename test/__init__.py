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

from __future__ import with_statement

import datetime
import functools
import os
import sys
import time
import unittest

import pymongo
import pymongo.errors
from nose.plugins.skip import SkipTest
from pymongo.mongo_client import _partition_node
from tornado import gen, ioloop
from tornado.stack_context import ExceptionStackContext

import motor

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None


host = os.environ.get("DB_IP", "localhost")
port = int(os.environ.get("DB_PORT", 27017))


def async_test_engine(timeout_sec=5, io_loop=None):
    if timeout_sec is not None and not isinstance(timeout_sec, (int, float)):
        raise TypeError("""\
Expected int or float, got %r
Use async_test_engine like:
    @async_test_engine()
or:
    @async_test_engine(timeout_sec=10)""" % timeout_sec)

    timeout_sec = max(float(os.environ.get('TIMEOUT_SEC', 0)), timeout_sec)

    def decorator(func):
        @functools.wraps(func)
        def _async_test(self):
            loop = io_loop or ioloop.IOLoop.instance()
            start = time.time()
            is_done = [False]
            error = [None]

            def on_exception(exc_type, exc_value, exc_traceback):
                error[0] = exc_value
                loop.stop()

            def done():
                is_done[0] = True
                loop.stop()

            def start_test():
                gen.engine(func)(self, done)

            def on_timeout():
                error[0] = AssertionError(
                    '%s timed out after %.2f seconds' % (
                        func, time.time() - start))
                loop.stop()

            timeout = loop.add_timeout(start + timeout_sec, on_timeout)

            with ExceptionStackContext(on_exception):
                loop.add_callback(start_test)

            loop.start()
            loop.remove_timeout(timeout)
            if error[0]:
                raise error[0]

            if not is_done[0]:
                raise Exception('%s did not call done()' % func)

        return _async_test
    return decorator

async_test_engine.__test__ = False  # Nose otherwise mistakes it for a test


class AssertRaises(gen.Task):
    def __init__(self, exc_type, func, *args, **kwargs):
        super(AssertRaises, self).__init__(func, *args, **kwargs)
        if not isinstance(exc_type, type):
            raise TypeError("%s is not a class" % repr(exc_type))

        if not issubclass(exc_type, Exception):
            raise TypeError(
                "%s is not a subclass of Exception" % repr(exc_type))
        self.exc_type = exc_type

    def get_result(self):
        (result, error), _ = self.runner.pop_result(self.key)
        if not isinstance(error, self.exc_type):
            if error:
                raise AssertionError("%s raised instead of %s" % (
                    repr(error), self.exc_type.__name__))
            else:
                raise AssertionError("%s not raised" % self.exc_type.__name__)
        return result


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


class MotorTest(unittest.TestCase):
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

        self.open_cursors = self.get_open_cursors()

    def get_open_cursors(self):
        # TODO: we've found this unreliable in PyMongo testing; find instead a
        # way to track cursors Motor creates and assert they're all closed
        output = self.sync_cx.admin.command('serverStatus')
        return output.get('cursors', {}).get('totalOpen', 0)

    @gen.engine
    def wait_for_cursors(self, callback):
        """Ensure any cursors opened during the test have been closed on the
        server. `yield motor.Op(cursor.close)` is usually simpler.
        """
        timeout_sec = float(os.environ.get('TIMEOUT_SEC', 5)) - 1
        loop = ioloop.IOLoop.instance()
        start = time.time()
        while self.get_open_cursors() > self.open_cursors:
            if time.time() - start > timeout_sec:
                self.fail("Waited too long for cursors to close")

            yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        callback()

    def motor_client(self, host, port, *args, **kwargs):
        """Get an open MotorClient. Ignores self.ssl, you must pass 'ssl'
           argument.
        """
        return motor.MotorClient(host, port, *args, **kwargs).open_sync()

    @gen.engine
    def check_callback_handling(self, fn, required, callback):
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
        try:
            self.assertRaises(TypeError, fn, callback='foo')
            self.assertRaises(TypeError, fn, callback=1)

            if required:
                self.assertRaises(TypeError, fn)
                self.assertRaises(TypeError, fn, None)
            else:
                # Should not raise
                fn(callback=None)

                # Let it finish so it doesn't interfere with future tests
                loop = ioloop.IOLoop.instance()
                yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=1))

            # Should not raise
            yield motor.Op(fn)
            callback(None, None)
        except Exception, e:
            callback(None, e)

    @gen.engine
    def check_required_callback(self, fn, *args, **kwargs):
        callback = kwargs.pop('callback')
        self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), True, callback=callback)

    @gen.engine
    def check_optional_callback(self, fn, *args, **kwargs):
        callback = kwargs.pop('callback')
        self.check_callback_handling(
            functools.partial(fn, *args, **kwargs), False, callback=callback)

    def tearDown(self):
        self.sync_coll.drop()

        # Replication cursors come and go, making this check unreliable against
        # replica sets.
        if not self.is_replica_set:
            if 'PyPy' in sys.version:
                import gc
                gc.collect()
                time.sleep(1)

            actual_open_cursors = self.get_open_cursors()
            self.assertEqual(
                self.open_cursors,
                actual_open_cursors,
                "%d open cursors at start of test, %d at end, should be equal"
                % (self.open_cursors, actual_open_cursors))

        super(MotorTest, self).tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
        if not self.is_replica_set:
            raise SkipTest("Not connected to a replica set")
