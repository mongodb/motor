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

import functools
import os
import time
import sys
import types
import unittest

import pymongo
import pymongo.errors
from tornado import gen, ioloop
from nose.plugins.skip import SkipTest
from pymongo.mongo_client import MongoClient, _partition_node

import motor

have_ssl = True
try:
    import ssl
except ImportError:
    have_ssl = False


host = os.environ.get("DB_IP", "localhost")
port = int(os.environ.get("DB_PORT", 27017))


# TODO: replicate asyncmongo's whole test suite?

class AsyncTestRunner(gen.Runner):
    def __init__(self, gen, timeout):
        # Tornado 2.3 added a second argument to Runner()
        super(AsyncTestRunner, self).__init__(gen, lambda: None)
        self.timeout = timeout

    def run(self):
        loop = ioloop.IOLoop.instance()

        try:
            super(AsyncTestRunner, self).run()
        except:
            loop.remove_timeout(self.timeout)
            loop.stop()
            raise

        if self.finished:
            loop.remove_timeout(self.timeout)
            loop.stop()


def async_test_engine(timeout_sec=None, io_loop=None):
    if (
        timeout_sec is not None
        and not isinstance(timeout_sec, int) and
        not isinstance(timeout_sec, float)
    ):
        raise TypeError(
"""Expected int or float, got %s
Use async_test_engine like:
    @async_test_engine()
or:
    @async_test_engine(timeout_sec=10)""" % (
        repr(timeout_sec)))

    if timeout_sec is None:
        timeout_sec = float(os.environ.get('TIMEOUT_SEC', 5))

    is_done = [False]

    def decorator(func):
        def done():
            is_done[0] = True

        @functools.wraps(func)
        def _async_test(self):
            # Uninstall previous loop
            if hasattr(ioloop.IOLoop, '_instance'):
                del ioloop.IOLoop._instance

            loop = io_loop or ioloop.IOLoop.instance()
            assert not loop._stopped
            if io_loop:
                io_loop.install()

            def on_timeout():
                loop.stop()
                raise AssertionError("%s timed out" % func)

            timeout = loop.add_timeout(time.time() + timeout_sec, on_timeout)

            try:
                generator = func(self, done)
                assert isinstance(generator, types.GeneratorType), (
                    "%s should be a generator, include a yield "
                    "statement" % func
                )

                runner = AsyncTestRunner(generator, timeout)
                runner.run()
                loop.start()
                if not runner.finished:
                    # Something stopped the loop before func could finish or
                    # throw an exception.
                    raise Exception('%s did not finish' % func)

                if not is_done[0]:
                    raise Exception('%s did not call done()' % func)
            finally:
                del ioloop.IOLoop._instance # Uninstall

        return _async_test
    return decorator

async_test_engine.__test__ = False # Nose otherwise mistakes it for a test


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
    longMessage = True # Used by unittest.TestCase
    ssl = False # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super(MotorTest, self).setUp()

        # Store a regular synchronous pymongo Connection for convenience while
        # testing. Set a timeout so we don't hang a test because, say, Mongo
        # isn't up or is hung by a long-running $where clause.
        connectTimeoutMS = socketTimeoutMS = 30 * 1000
        if self.ssl:
            if not have_ssl:
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

    def motor_connection(self, host, port, *args, **kwargs):
        """Get an open MotorClient. Ignores self.ssl, you must pass 'ssl'
           argument.
        """
        return motor.MotorClient(host, port, *args, **kwargs).open_sync()

    def check_callback_handling(self, fn, required):
        """
        Take a function and verify that it accepts a 'callback' parameter
        and properly type-checks it. If 'required', check that fn requires
        a callback.
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
        fn(callback=lambda result, error: None)

    def check_required_callback(self, fn, *args, **kwargs):
        self.check_callback_handling(
            functools.partial(fn, *args, **kwargs),
            True)

    def check_optional_callback(self, fn, *args, **kwargs):
        self.check_callback_handling(
            functools.partial(fn, *args, **kwargs),
            False)

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


class MotorTestBasic(MotorTest):
    def test_repr(self):
        cx = self.motor_connection(host, port)
        self.assertTrue(repr(cx).startswith('MotorClient'))
        db = cx.pymongo_test
        self.assertTrue(repr(db).startswith('MotorDatabase'))
        coll = db.test_collection
        self.assertTrue(repr(coll).startswith('MotorCollection'))


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
        if not self.is_replica_set:
            raise SkipTest("Not connected to a replica set")
