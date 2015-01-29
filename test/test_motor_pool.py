# Copyright 2013-2014 MongoDB, Inc.
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

import functools
import greenlet
import random
import unittest

import pymongo.errors
from tornado import gen, stack_context
from tornado.concurrent import Future
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, assert_raises, SkipTest, host, port
from test.utils import delay, one


class MotorPoolTest(MotorTest):
    @gen_test
    def test_max_size_default(self):
        yield self.cx.open()
        pool = self.cx._get_primary_pool()

        # Current defaults
        self.assertEqual(100, pool.max_size)
        self.assertEqual(None, pool.wait_queue_timeout)
        self.assertEqual(None, pool.wait_queue_multiple)

    @gen_test(timeout=30)
    def test_max_size(self):
        if not test.env.v8:
            raise SkipTest("Need multithreaded Javascript in mongod for test")

        max_pool_size = 5
        cx = self.motor_client(max_pool_size=max_pool_size)

        # Lazy connection.
        self.assertEqual(None, cx._get_primary_pool())
        yield cx.motor_test.test_collection.remove()
        pool = cx._get_primary_pool()
        self.assertEqual(max_pool_size, pool.max_size)
        self.assertEqual(1, len(pool.sockets))
        self.assertEqual(1, pool.motor_sock_counter)

        # Grow to max_pool_size.
        ops_completed = Future()
        nops = 100
        results = []

        def callback(i, result, error):
            self.assertFalse(error)
            self.assertFalse(pool.motor_sock_counter > max_pool_size)
            results.append(i)
            if len(results) == nops:
                ops_completed.set_result(None)

        collection = cx.motor_test.test_collection
        yield collection.insert({})  # Need a document.

        for i in range(nops):
            # Introduce random delay, avg 5ms, just to make sure we're async.
            collection.find_one(
                {'$where': delay(random.random() / 10)},
                callback=functools.partial(callback, i))

        yield ops_completed

        # All ops completed, but not in order.
        self.assertEqual(list(range(nops)), sorted(results))
        self.assertNotEqual(list(range(nops)), results)

        self.assertEqual(max_pool_size, len(pool.sockets))
        self.assertEqual(max_pool_size, pool.motor_sock_counter)
        cx.close()

    @gen_test(timeout=30)
    def test_force(self):
        cx = self.motor_client(max_pool_size=2, waitQueueTimeoutMS=100)
        yield cx.open()
        pool = cx._get_primary_pool()

        def get_socket():
            s = pool.get_socket(force=True)
            self.io_loop.add_callback(functools.partial(future.set_result, s))

        future = Future()
        greenlet.greenlet(get_socket).switch()
        socket_info = yield future
        self.assertEqual(1, pool.motor_sock_counter)

        future = Future()
        greenlet.greenlet(get_socket).switch()
        socket_info2 = yield future
        self.assertEqual(2, pool.motor_sock_counter)

        future = Future()
        greenlet.greenlet(get_socket).switch()
        forced_socket_info = yield future
        self.assertEqual(3, pool.motor_sock_counter)

        future = Future()
        greenlet.greenlet(get_socket).switch()
        forced_socket_info2 = yield future
        self.assertEqual(4, pool.motor_sock_counter)

        # First returned sockets are closed, since our outstanding sockets
        # exceed max_pool_size.
        pool.maybe_return_socket(socket_info)
        self.assertTrue(socket_info.closed)
        self.assertEqual(0, len(pool.sockets))
        self.assertEqual(3, pool.motor_sock_counter)

        pool.maybe_return_socket(socket_info2)
        self.assertTrue(socket_info2.closed)
        self.assertEqual(0, len(pool.sockets))
        self.assertEqual(2, pool.motor_sock_counter)

        # Closed socket isn't pooled, but motor_sock_counter is decremented.
        forced_socket_info.close()
        pool.maybe_return_socket(forced_socket_info)
        self.assertEqual(0, len(pool.sockets))
        self.assertEqual(1, pool.motor_sock_counter)

        # Returned socket is pooled, motor_sock_counter not decremented.
        pool.maybe_return_socket(forced_socket_info2)
        self.assertFalse(forced_socket_info2.closed)
        self.assertEqual(1, len(pool.sockets))
        self.assertEqual(1, pool.motor_sock_counter)

        cx.close()

    @gen_test(timeout=30)
    def test_wait_queue_timeout(self):
        # Do a find_one that takes 1 second, and set waitQueueTimeoutMS to 500,
        # 5000, and None. Verify timeout iff max_wait_time < 1 sec.
        where_delay = 1
        yield self.collection.insert({})
        for waitQueueTimeoutMS in (500, 5000, None):
            cx = self.motor_client(
                max_pool_size=1, waitQueueTimeoutMS=waitQueueTimeoutMS)

            yield cx.open()
            pool = cx._get_primary_pool()
            if waitQueueTimeoutMS:
                self.assertEqual(
                    waitQueueTimeoutMS, pool.wait_queue_timeout * 1000)
            else:
                self.assertTrue(pool.wait_queue_timeout is None)

            collection = cx.motor_test.test_collection
            future = collection.find_one({'$where': delay(where_delay)})
            if waitQueueTimeoutMS and waitQueueTimeoutMS < where_delay * 1000:
                with assert_raises(pymongo.errors.ConnectionFailure):
                    yield collection.find_one()
            else:
                # No error
                yield collection.find_one()
            yield future
            cx.close()

    @gen_test(timeout=30)
    def test_wait_queue_multiple(self):
        cx = self.motor_client(max_pool_size=2,
                               waitQueueTimeoutMS=100,
                               waitQueueMultiple=3)
        yield cx.open()
        pool = cx._get_primary_pool()

        def get_socket_on_greenlet(future):
            try:
                s = pool.get_socket()
                future.set_result(s)
            except Exception as e:
                future.set_exception(e)

        def get_socket():
            future = Future()
            fn = functools.partial(get_socket_on_greenlet, future)
            greenlet.greenlet(fn).switch()
            return future

        s1 = yield get_socket()
        self.assertEqual(1, pool.motor_sock_counter)

        s2 = yield get_socket()
        self.assertEqual(2, pool.motor_sock_counter)

        start = self.io_loop.time()
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield get_socket()

        # 100-millisecond timeout.
        self.assertAlmostEqual(0.1, self.io_loop.time() - start, places=1)
        self.assertEqual(2, pool.motor_sock_counter)

        # Give a socket back to the pool, a waiter receives it.
        s1_future = get_socket()
        pool.maybe_return_socket(s1)
        self.assertEqual(s1, (yield s1_future))
        self.assertEqual(2, pool.motor_sock_counter)

        # max_pool_size * waitQueueMultiple = 6 waiters are allowed.
        for _ in range(6):
            get_socket()

        start = self.io_loop.time()
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield get_socket()

        # Fails immediately.
        self.assertAlmostEqual(0, self.io_loop.time() - start, places=3)
        self.assertEqual(2, pool.motor_sock_counter)
        cx.close()

    @gen_test
    def test_connections_unacknowledged_writes(self):
        # Verifying that unacknowledged writes don't open extra connections
        collection = self.cx.motor_test.test_collection
        yield collection.drop()
        pool = self.cx._get_primary_pool()
        self.assertEqual(1, pool.motor_sock_counter)

        nops = 10
        for i in range(nops - 1):
            collection.insert({'_id': i}, w=0)

            # We have only one socket open, and it's already back in the pool
            self.assertEqual(1, pool.motor_sock_counter)
            self.assertEqual(1, len(pool.sockets))

        # Acknowledged write; uses same socket and blocks for all inserts
        yield collection.insert({'_id': nops - 1})
        self.assertEqual(1, pool.motor_sock_counter)

        # Socket is back in the idle pool
        self.assertEqual(1, len(pool.sockets))

        # All ops completed
        docs = yield collection.find().sort('_id').to_list(length=100)
        self.assertEqual(list(range(nops)), [doc['_id'] for doc in docs])

    @gen_test
    def test_check_socket(self):
        # Test that MotorPool._check(socket_info) replaces a closed socket
        # and doesn't leak a counter.
        yield self.cx.open()
        pool = self.cx._get_primary_pool()
        pool._check_interval_seconds = 0  # Always check.
        counter = pool.motor_sock_counter
        sock_info = one(pool.sockets)
        sock_info.sock.close()
        pool.maybe_return_socket(sock_info)

        # New socket replaces closed one.
        yield self.cx.server_info()
        sock_info2 = one(pool.sockets)
        self.assertNotEqual(sock_info, sock_info2)

        # Counter isn't leaked.
        self.assertEqual(counter, pool.motor_sock_counter)

    @gen_test
    def test_stack_context(self):
        # See http://tornadoweb.org/en/stable/stack_context.html
        # MotorPool.get_socket can block waiting for a callback in another
        # context to return a socket. We verify MotorPool's stack-context
        # handling by testing that exceptions raised in get_socket's
        # continuation are caught in get_socket's stack context, not
        # return_socket's.

        loop = self.io_loop
        history = []
        cx = self.motor_client(max_pool_size=1)

        # Open a socket
        yield cx.motor_test.test_collection.find_one()

        pool = cx._get_primary_pool()
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
            # Blocks until socket is available, since max_pool_size is 1.
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

        with stack_context.ExceptionStackContext(catch_get_sock_exc):
            loop.add_callback(greenlet.greenlet(get_socket).switch)

        greenlet.greenlet(return_socket).switch()
        yield self.pause(0.1)

        # 'return_sock_exc' was *not* added to history, because stack context
        # wasn't leaked from return_socket to get_socket.
        self.assertEqual(['raise', 'get_sock_exc', my_assert], history)
        cx.close()

    @gen_test
    def test_resolve_stack_context(self):
        # See http://tornadoweb.org/en/stable/stack_context.html
        # MotorPool can switch contexts while resolving a name, test that
        # an exception raised after resolution propagates correctly.
        future = Future()
        my_assert = AssertionError('foo')

        pool = motor.MotorPool(
            io_loop=self.io_loop,
            pair=(host, port),
            max_size=1,
            net_timeout=None,
            conn_timeout=100,
            use_ssl=False,
            use_greenlets=None)

        def get_socket():
            # This leads to a call to pool.resolve(), which switches contexts
            # and must restore properly.
            pool.get_socket()
            self.io_loop.add_callback(raise_callback)

        def raise_callback():
            raise my_assert

        def catch_get_sock_exc(exc_type, exc_value, exc_traceback):
            future.set_exception(exc_value)

            # Don't propagate.
            return True

        with stack_context.ExceptionStackContext(catch_get_sock_exc):
            self.io_loop.add_callback(greenlet.greenlet(get_socket).switch)

        with self.assertRaises(AssertionError) as context:
            yield future

        self.assertEqual(context.exception, my_assert)


if __name__ == '__main__':
    unittest.main()
