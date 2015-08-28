# Copyright 2013-2015 MongoDB, Inc.
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

import asyncio
import functools
import greenlet
import random
import unittest

import pymongo.errors

import test
from test.asyncio_tests import asyncio_test, AsyncIOTestCase
from test import assert_raises, SkipTest
from test.utils import delay, one


class AIOMotorPoolTest(AsyncIOTestCase):
    @asyncio_test
    def test_max_size_default(self):
        yield from self.cx.open()
        pool = self.cx._get_primary_pool()

        # Current defaults
        self.assertEqual(100, pool.max_size)
        self.assertEqual(None, pool.wait_queue_timeout)
        self.assertEqual(None, pool.wait_queue_multiple)

    @asyncio_test(timeout=30)
    def test_max_size(self):
        if not test.env.v8:
            raise SkipTest("Need multithreaded Javascript in mongod for test")

        max_pool_size = 5
        cx = self.asyncio_client(max_pool_size=max_pool_size)

        # Lazy connection.
        self.assertEqual(None, cx._get_primary_pool())
        yield from cx.motor_test.test_collection.remove()
        pool = cx._get_primary_pool()
        self.assertEqual(max_pool_size, pool.max_size)
        self.assertEqual(1, len(pool.sockets))
        self.assertEqual(1, pool.motor_sock_counter)

        # Grow to max_pool_size.
        ops_completed = asyncio.Future(loop=self.loop)
        nops = 100
        results = []

        def callback(i, result, error):
            self.assertFalse(error)
            self.assertFalse(pool.motor_sock_counter > max_pool_size)
            results.append(i)
            if len(results) == nops:
                ops_completed.set_result(None)

        collection = cx.motor_test.test_collection
        yield from collection.insert({})  # Need a document.

        for i in range(nops):
            # Introduce random delay, avg 5ms, just to make sure we're async.
            collection.find_one(
                {'$where': delay(random.random() / 10)},
                callback=functools.partial(callback, i))

        yield from ops_completed

        # All ops completed, but not in order.
        self.assertEqual(list(range(nops)), sorted(results))
        self.assertNotEqual(list(range(nops)), results)

        self.assertEqual(max_pool_size, len(pool.sockets))
        self.assertEqual(max_pool_size, pool.motor_sock_counter)
        cx.close()

    @asyncio_test(timeout=30)
    def test_force(self):
        cx = self.asyncio_client(max_pool_size=2, waitQueueTimeoutMS=100)
        yield from cx.open()
        pool = cx._get_primary_pool()

        def get_socket():
            s = pool.get_socket(force=True)
            self.loop.call_later(0, functools.partial(future.set_result, s))
            self.addCleanup(s.close)

        future = asyncio.Future(loop=self.loop)
        greenlet.greenlet(get_socket).switch()
        socket_info = yield from future
        self.assertEqual(1, pool.motor_sock_counter)

        future = asyncio.Future(loop=self.loop)
        greenlet.greenlet(get_socket).switch()
        socket_info2 = yield from future
        self.assertEqual(2, pool.motor_sock_counter)

        future = asyncio.Future(loop=self.loop)
        greenlet.greenlet(get_socket).switch()
        forced_socket_info = yield from future
        self.assertEqual(3, pool.motor_sock_counter)

        future = asyncio.Future(loop=self.loop)
        greenlet.greenlet(get_socket).switch()
        forced_socket_info2 = yield from future
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

    @asyncio_test(timeout=30)
    def test_wait_queue_timeout(self):
        # Do a find_one that takes 1 second, and set waitQueueTimeoutMS to 500,
        # 5000, and None. Verify timeout iff max_wait_time < 1 sec.
        where_delay = 1
        yield from self.collection.insert({})
        for waitQueueTimeoutMS in (500, 5000, None):
            cx = self.asyncio_client(
                max_pool_size=1, waitQueueTimeoutMS=waitQueueTimeoutMS)

            yield from cx.open()
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
                    yield from collection.find_one()
            else:
                # No error
                yield from collection.find_one()
            yield from future
            cx.close()

    @asyncio_test(timeout=30)
    def test_wait_queue_multiple(self):
        cx = self.asyncio_client(max_pool_size=2,
                                 waitQueueTimeoutMS=100,
                                 waitQueueMultiple=3)
        yield from cx.open()
        pool = cx._get_primary_pool()

        def get_socket_on_greenlet(future):
            try:
                s = pool.get_socket()
                future.set_result(s)
            except Exception as e:
                future.set_exception(e)

        def get_socket():
            future = asyncio.Future(loop=self.loop)
            fn = functools.partial(get_socket_on_greenlet, future)
            greenlet.greenlet(fn).switch()
            return future

        s1 = yield from get_socket()
        self.assertEqual(1, pool.motor_sock_counter)

        yield from get_socket()
        self.assertEqual(2, pool.motor_sock_counter)

        start = self.loop.time()

        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield from get_socket()

        # 100-millisecond timeout.
        self.assertAlmostEqual(0.1, self.loop.time() - start, places=1)
        self.assertEqual(2, pool.motor_sock_counter)

        # Give a socket back to the pool, a waiter receives it.
        s1_future = get_socket()
        pool.maybe_return_socket(s1)
        self.assertEqual(s1, (yield from s1_future))
        self.assertEqual(2, pool.motor_sock_counter)

        # max_pool_size * waitQueueMultiple = 6 waiters are allowed.
        for _ in range(6):
            get_socket()

        start = self.loop.time()
        with self.assertRaises(pymongo.errors.ConnectionFailure):
            yield from get_socket()

        # Fails immediately.
        self.assertAlmostEqual(0, self.loop.time() - start, places=3)
        self.assertEqual(2, pool.motor_sock_counter)
        cx.close()
        yield from asyncio.sleep(0, loop=self.loop)

    @asyncio_test
    def test_connections_unacknowledged_writes(self):
        # Verifying that unacknowledged writes don't open extra connections
        collection = self.cx.motor_test.test_collection
        yield from collection.drop()
        pool = self.cx._get_primary_pool()
        self.assertEqual(1, pool.motor_sock_counter)

        nops = 10
        for i in range(nops - 1):
            collection.insert({'_id': i}, w=0)

            # We have only one socket open, and it's already back in the pool
            self.assertEqual(1, pool.motor_sock_counter)
            self.assertEqual(1, len(pool.sockets))

        # Acknowledged write; uses same socket and blocks for all inserts
        yield from collection.insert({'_id': nops - 1})
        self.assertEqual(1, pool.motor_sock_counter)

        # Socket is back in the idle pool
        self.assertEqual(1, len(pool.sockets))

        # All ops completed
        docs = yield from collection.find().sort('_id').to_list(length=100)
        self.assertEqual(list(range(nops)), [doc['_id'] for doc in docs])

    @asyncio_test
    def test_check_socket(self):
        # Test that MotorPool._check(socket_info) replaces a closed socket
        # and doesn't leak a counter.
        yield from self.cx.open()
        pool = self.cx._get_primary_pool()
        pool._check_interval_seconds = 0  # Always check.
        counter = pool.motor_sock_counter
        sock_info = one(pool.sockets)
        sock_info.sock.close()
        pool.maybe_return_socket(sock_info)

        # New socket replaces closed one.
        yield from self.cx.server_info()
        sock_info2 = one(pool.sockets)
        self.assertNotEqual(sock_info, sock_info2)

        # Counter isn't leaked.
        self.assertEqual(counter, pool.motor_sock_counter)


if __name__ == '__main__':
    unittest.main()
