# Copyright 2013 10gen, Inc.
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
import greenlet
import random
import unittest

from nose.plugins.skip import SkipTest
from pymongo.errors import ConfigurationError
from tornado import gen, stack_context
from tornado.ioloop import IOLoop

import motor
from test import host, port, MotorTest, async_test_engine, AssertRaises
from test.utils import delay


class MotorPoolTest(MotorTest):
    def test_max_concurrent_default(self):
        # pool.max_size, which is actually the max number of *idle* sockets,
        # defaults to 10 in PyMongo. Our max_concurrent defaults to 100.
        cx = motor.MotorClient(host, port).open_sync()
        pool = cx.delegate._MongoClient__pool

        # Current defaults
        self.assertEqual(10, pool.max_size)
        self.assertEqual(100, pool.max_concurrent)

    def test_max_concurrent_validation(self):
        self.assertRaises(ConfigurationError,
            motor.MotorClient(host, port, max_concurrent=-1).open_sync)

        self.assertRaises(TypeError,
            motor.MotorClient(host, port, max_concurrent=None).open_sync)

        self.assertRaises(TypeError,
            motor.MotorClient(host, port, max_concurrent=1.5).open_sync)

    def test_max_wait_default(self):
        cx = motor.MotorClient(host, port).open_sync()
        pool = cx.delegate._MongoClient__pool
        self.assertEqual(None, pool.max_wait_time)

    def test_max_wait_validation(self):
        self.assertRaises(ConfigurationError,
            motor.MotorClient(host, port, max_wait_time=-1).open_sync)

        self.assertRaises(ConfigurationError,
            motor.MotorClient(host, port, max_wait_time=0).open_sync)

        self.assertRaises(ConfigurationError,
            motor.MotorClient(host, port, max_wait_time='foo').open_sync)

        # Ok
        motor.MotorClient(host, port, max_wait_time=None).open_sync()
        motor.MotorClient(host, port, max_wait_time=100).open_sync()

    @async_test_engine(timeout_sec=30)
    def test_max_concurrent(self, done):
        if not self.sync_cx.server_info().get('javascriptEngine') == 'V8':
            raise SkipTest("Need multithreaded Javascript in mongod for test")

        # Make sure we can override max_size and max_concurrent
        max_pool_size = 5
        max_concurrent = 20

        cx = motor.MotorClient(
            host, port,
            max_pool_size=max_pool_size, max_concurrent=max_concurrent
        ).open_sync()

        pool = cx._get_pools()[0]
        self.assertEqual(max_pool_size, pool.max_size)
        self.assertEqual(max_concurrent, pool.max_concurrent)

        # Start empty
        self.assertEqual(0, pool.motor_sock_counter.count())
        self.assertEqual(0, len(pool.sockets))

        # Grow to max_concurrent
        ops_completed = yield gen.Callback('ops_completed')
        nops = 100
        results = []
        def callback(i, result, error):
            self.assertFalse(error)
            results.append(i)
            if len(results) == nops:
                ops_completed()

        collection = cx.pymongo_test.test_collection
        for i in range(nops):
            # Introduce random delay, avg 5ms, just to make sure we're async
            collection.find_one({'$where': delay(random.random() / 10)},
                callback=functools.partial(callback, i))

            # Active sockets tops out at max_concurrent, which defaults to 100
            expected_active_socks = min(max_concurrent, i + 1)
            self.assertEqual(
                expected_active_socks, pool.motor_sock_counter.count())

            self.assertEqual(0, len(pool.sockets))

        yield gen.Wait('ops_completed')

        # All ops completed, but not in order
        self.assertEqual(list(range(nops)), sorted(results))
        self.assertNotEqual(list(range(nops)), results)

        # Shrunk back to max_pool_size
        self.assertEqual(max_pool_size, pool.motor_sock_counter.count())
        self.assertEqual(max_pool_size, len(pool.sockets))

        done()

    @async_test_engine(timeout_sec=10)
    def test_max_wait(self, done):
        # Do a find_one that takes 1 second, and set max_wait_time to .5 sec,
        # 1 sec, and None. Verify timeout iff max_wait_time < 1 sec.
        where_delay = 1
        for max_wait_time in .5, 2, None:
            cx = motor.MotorClient(
                host, port, max_concurrent=1, max_wait_time=max_wait_time,
            ).open_sync()

            pool = cx._get_pools()[0]
            self.assertEqual(max_wait_time, pool.max_wait_time)
            collection = cx.pymongo_test.test_collection
            cb = yield gen.Callback('find_one')
            collection.find_one({'$where': delay(where_delay)}, callback=cb)
            if max_wait_time and max_wait_time < where_delay:
                yield AssertRaises(motor.MotorPoolTimeout, collection.find_one)
            else:
                # No error
                yield motor.Op(collection.find_one)
            yield gen.Wait('find_one')

        done()

    @async_test_engine(timeout_sec=30)
    def test_connections_unacknowledged_writes(self, done):
        # Verifying that unacknowledged writes don't open extra connections
        cx = motor.MotorClient(host, port).open_sync()
        pool = cx.delegate._MongoClient__pool
        collection = cx.pymongo_test.test_collection
        yield motor.Op(collection.drop)
        self.assertEqual(1, pool.motor_sock_counter.count())

        nops = 10
        for i in range(nops - 1):
            collection.insert({'_id': i}, w=0)

            # We have only one socket open, and it's already back in the pool
            self.assertEqual(1, pool.motor_sock_counter.count())
            self.assertEqual(1, len(pool.sockets))

        # Acknowledged write; uses same socket and blocks for all inserts
        yield motor.Op(collection.insert, {'_id': nops - 1})
        self.assertEqual(1, pool.motor_sock_counter.count())

        # Socket is back in the idle pool
        self.assertEqual(1, len(pool.sockets))

        # All ops completed
        docs = yield motor.Op(collection.find().sort('_id').to_list)
        self.assertEqual(list(range(nops)), [doc['_id'] for doc in docs])

        done()

    @async_test_engine()
    def test_stack_context(self, done):
        # See http://www.tornadoweb.org/documentation/stack_context.html
        # MotorPool.get_socket can block waiting for a callback in another
        # context to return a socket. We verify MotorPool's stack-context
        # handling by testing that exceptions raised in get_socket's
        # continuation are caught in get_socket's stack context, not
        # return_socket's.

        loop = IOLoop.instance()
        history = []
        cx = yield motor.Op(
            motor.MotorClient(host, port, max_concurrent=1).open)

        pool = cx._get_pools()[0]
        self.assertEqual(1, len(pool.sockets))
        sock_info = pool.get_socket()

        main_gr = greenlet.getcurrent()

        def catch_get_sock_exc(exc_type, exc_value, exc_traceback):
            history.extend(['get_sock_exc', exc_value])
            return True  # Don't propagate

        def catch_return_sock_exc(exc_type, exc_value, exc_traceback):
            history.extend(['return_sock_exc', exc_value])
            return True  # Don't propagate

        def get_socket():
            with stack_context.ExceptionStackContext(catch_get_sock_exc):
                # Blocks until socket is available, since max_concurrent is 1
                pool.get_socket()
                loop.add_callback(raise_callback)

        my_assert = AssertionError('foo')

        def raise_callback():
            history.append('raise')
            raise my_assert

        def return_socket():
            with stack_context.ExceptionStackContext(catch_return_sock_exc):
                pool.maybe_return_socket(sock_info)

            main_gr.switch()

        greenlet.greenlet(get_socket).switch()
        greenlet.greenlet(return_socket).switch()

        yield gen.Task(loop.add_timeout, datetime.timedelta(seconds=0.1))

        # 'return_sock_exc' was *not* added to history, because stack context
        # wasn't leaked from return_socket to get_socket.
        self.assertEqual(['raise', 'get_sock_exc', my_assert], history)
        done()

if __name__ == '__main__':
    unittest.main()
