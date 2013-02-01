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

import functools
import random
import unittest

from nose.plugins.skip import SkipTest
from pymongo.errors import ConfigurationError
from tornado import gen

import motor
from test import host, port, MotorTest, async_test_engine
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

        self.assertRaises(ConfigurationError,
            motor.MotorClient(host, port, max_concurrent=-1).open_sync)

        self.assertRaises(TypeError,
            motor.MotorClient(host, port, max_concurrent=None).open_sync)

        self.assertRaises(TypeError,
            motor.MotorClient(host, port, max_concurrent=1.5).open_sync)

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

        pool = cx.delegate._MongoClient__pool
        self.assertEqual(max_pool_size, pool.max_size)
        self.assertEqual(max_concurrent, pool.max_concurrent)

        # Start empty
        self.assertEqual(0, pool.motor_sock_counter.count())
        self.assertEqual(0, len(pool.sockets))

        # Grow to max_concurrent
        ops_completed = yield gen.Callback('ops_completed')
        nops = 500
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


if __name__ == '__main__':
    unittest.main()
