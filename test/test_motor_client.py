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

import time
import unittest

import pymongo
from tornado import ioloop, gen
from pymongo.errors import InvalidOperation, ConfigurationError
from pymongo.errors import ConnectionFailure

import motor
from test import host, port
from test import MotorTest, async_test_engine, AssertRaises, AssertEqual
from test.utils import server_is_master_with_slave, delay


class MotorClientTest(MotorTest):
    @async_test_engine()
    def test_connection(self, done):
        cx = motor.MotorClient(host, port)

        # Can't access databases before connecting
        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx.some_database_name
        )

        self.assertRaises(
            pymongo.errors.InvalidOperation,
            lambda: cx['some_database_name']
        )

        result = yield motor.Op(cx.open)
        self.assertEqual(result, cx)
        self.assertTrue(cx.connected)

        # Ensure callback is re-executed if already connected
        yield AssertEqual(cx, cx.open)
        self.assertEqual(cx, cx.open_sync())
        done()

    def test_connection_callback(self):
        cx = motor.MotorClient(host, port)
        self.check_optional_callback(cx.open)

    def test_disconnect(self):
        cx = motor.MotorClient(host, port).open_sync()
        cx.disconnect()
        self.assertEqual(0, len(cx.delegate._MongoClient__pool.sockets))

    @async_test_engine()
    def test_sync_client(self, done):
        class DictSubclass(dict):
            pass

        args = host, port
        kwargs = dict(
            connectTimeoutMS=1000, socketTimeoutMS=1500, max_pool_size=23,
            document_class=DictSubclass, tz_aware=True)

        cx = yield motor.Op(motor.MotorClient(*args, **kwargs).open)
        sync_cx = cx.sync_client()
        self.assertTrue(isinstance(sync_cx, pymongo.mongo_client.MongoClient))
        self.assertEqual(host, sync_cx.host)
        self.assertEqual(port, sync_cx.port)
        self.assertEqual(1000, sync_cx._MongoClient__conn_timeout * 1000.0)
        self.assertEqual(1500, sync_cx._MongoClient__net_timeout * 1000.0)
        self.assertEqual(23, sync_cx._MongoClient__max_pool_size)
        self.assertEqual(True, sync_cx._MongoClient__tz_aware)
        self.assertEqual(DictSubclass, sync_cx._MongoClient__document_class)

        # Make sure sync connection works
        self.assertEqual(
            {'_id': 5, 's': hex(5)},
            sync_cx.pymongo_test.test_collection.find_one({'_id': 5}))

        done()

    @async_test_engine()
    def test_open_sync(self, done):
        loop = ioloop.IOLoop.instance()
        cx = motor.MotorClient(host, port)
        self.assertFalse(cx.connected)

        # open_sync() creates a special IOLoop just to run the connection
        # code to completion
        self.assertEqual(cx, cx.open_sync())
        self.assertTrue(cx.connected)

        # IOLoop was restored?
        self.assertEqual(loop, cx.io_loop)

        # Really connected?
        result = yield motor.Op(cx.admin.command, "buildinfo")
        self.assertEqual(int, type(result['bits']))

        yield motor.Op(cx.pymongo_test.test_collection.insert,
            {'_id': 'test_open_sync'})
        doc = yield motor.Op(
            cx.pymongo_test.test_collection.find_one, {'_id': 'test_open_sync'})
        self.assertEqual('test_open_sync', doc['_id'])
        done()

    def test_open_sync_custom_io_loop(self):
        # Check that we can create a MotorClient with a custom IOLoop, then
        # call open_sync(), which uses a new loop, and the custom loop is
        # restored.
        loop = ioloop.IOLoop()
        cx = motor.MotorClient(host, port, io_loop=loop)
        self.assertEqual(cx, cx.open_sync())
        self.assertTrue(cx.connected)

        # Custom loop restored?
        self.assertEqual(loop, cx.io_loop)

        @async_test_engine(io_loop=loop)
        def test(self, done):
            # Custom loop works?
            yield AssertEqual(
                {'_id': 17, 's': hex(17)},
                cx.pymongo_test.test_collection.find_one, {'_id': 17})

            yield AssertEqual(
                {'_id': 37, 's': hex(37)},
                cx.pymongo_test.test_collection.find_one, {'_id': 37})
            done()

        test(self)

    def test_custom_io_loop(self):
        self.assertRaises(
            TypeError,
            lambda: motor.MotorClient(host, port, io_loop='foo')
        )

        loop = ioloop.IOLoop()

        @async_test_engine(io_loop=loop)
        def test(self, done):
            # Make sure we can do async things with the custom loop
            cx = motor.MotorClient(host, port, io_loop=loop)
            yield AssertEqual(cx, cx.open)
            self.assertTrue(cx.connected)
            doc = yield motor.Op(
                cx.pymongo_test.test_collection.find_one, {'_id': 17})
            self.assertEqual({'_id': 17, 's': hex(17)}, doc)
            done()

        test(self)

    def test_database_named_delegate(self):
        cx = self.motor_connection(host, port)
        self.assertTrue(
            isinstance(cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(cx['delegate'], motor.MotorDatabase))

    def test_copy_db_argument_checking(self):
        cx = self.motor_connection(host, port)

        self.assertRaises(TypeError, cx.copy_database, 4, "foo")
        self.assertRaises(TypeError, cx.copy_database, "foo", 4)

        self.assertRaises(
            pymongo.errors.InvalidName, cx.copy_database, "foo", "$foo")

    @async_test_engine(timeout_sec=600)
    def test_copy_db(self, done):
        # 1. Drop old test DBs
        # 2. Copy a test DB N times at once (we need to do it many times at
        #   once to make sure that GreenletPool's start_request() is properly
        #   isolating operations from each other)
        # 3. Create a username and password
        # 4. Copy a database using name and password
        is_ms = server_is_master_with_slave(self.sync_cx)
        ncopies = 10
        nrange = list(range(ncopies))
        test_db_names = ['pymongo_test%s' % i for i in nrange]
        cx = self.motor_connection(host, port)

        def check_copydb_results():
            db_names = self.sync_cx.database_names()
            for test_db_name in test_db_names:
                self.assertTrue(test_db_name in db_names)
                result = self.sync_cx[test_db_name].test_collection.find_one()
                self.assertTrue(result, "No results in %s" % test_db_name)
                self.assertEqual("bar", result.get("foo"),
                    "Wrong result from %s: %s" % (test_db_name, result))

        def drop_all():
            for test_db_name in test_db_names:
                # Setup code has configured a short timeout, and the copying
                # has put Mongo under enough load that we risk timeouts here
                # unless we override.
                self.sync_cx[test_db_name]['$cmd'].find_one(
                    {'dropDatabase': 1}, network_timeout=30)

            if not is_ms:
                # Due to SERVER-2329, databases may not disappear from a master
                # in a master-slave pair
                db_names = self.sync_cx.database_names()
                for test_db_name in test_db_names:
                    self.assertFalse(
                        test_db_name in db_names,
                        "%s not dropped" % test_db_name)

        # 1. Drop old test DBs
        yield motor.Op(cx.drop_database, 'pymongo_test')
        drop_all()

        # 2. Copy a test DB N times at once
        yield motor.Op(cx.pymongo_test.test_collection.insert, {"foo": "bar"})
        for test_db_name in test_db_names:
            cx.copy_database("pymongo_test", test_db_name,
                callback=(yield gen.Callback(key=test_db_name)))

        yield motor.WaitAllOps(test_db_names)
        check_copydb_results()

        drop_all()

        # 3. Create a username and password
        yield motor.Op(cx.pymongo_test.add_user, "mike", "password")

        yield AssertRaises(
            pymongo.errors.OperationFailure,
            cx.copy_database, "pymongo_test", "pymongo_test0",
            username="foo", password="bar")

        yield AssertRaises(
            pymongo.errors.OperationFailure, cx.copy_database,
            "pymongo_test", "pymongo_test0",
            username="mike", password="bar")

        # 4. Copy a database using name and password
        for test_db_name in test_db_names:
            cx.copy_database(
                "pymongo_test", test_db_name,
                username="mike", password="password",
                callback=(yield gen.Callback(test_db_name)))

        yield motor.WaitAllOps(test_db_names)
        check_copydb_results()

        drop_all()
        done()

    @async_test_engine()
    def test_is_locked(self, done):
        cx = self.motor_connection(host, port)
        self.assertTrue((yield motor.Op(cx.is_locked)) is False)
        yield motor.Op(cx.fsync, lock=True)
        self.assertTrue((yield motor.Op(cx.is_locked)) is True)
        yield motor.Op(cx.unlock)
        self.assertTrue((yield motor.Op(cx.is_locked)) is False)
        done()

    @async_test_engine()
    def test_timeout(self, done):
        # Launch two slow find_ones. The one with a timeout should get an error
        no_timeout = self.motor_connection(host, port)
        timeout = self.motor_connection(host, port, socketTimeoutMS=100)
        query = {'$where': delay(0.5), '_id': 1}

        timeout.pymongo_test.test_collection.find_one(
            query, callback=(yield gen.Callback('timeout')))

        no_timeout.pymongo_test.test_collection.find_one(
            query, callback=(yield gen.Callback('no_timeout')))

        timeout_result, no_timeout_result = yield gen.WaitAll(
            ['timeout', 'no_timeout'])

        self.assertEqual(str(timeout_result.args[1]), 'timed out')
        self.assertTrue(
            isinstance(timeout_result.args[1], pymongo.errors.AutoReconnect))

        self.assertEqual({'_id':1, 's':hex(1)}, no_timeout_result.args[0])
        done()

    @async_test_engine()
    def test_connection_failure(self, done):
        exc = None
        try:
            # Assuming there isn't anything actually running on this port
            yield motor.Op(motor.MotorClient('localhost', 8765).open)
        except Exception, e:
            exc = e

        self.assertTrue(isinstance(exc, ConnectionFailure))
        done()

    @async_test_engine()
    def test_connection_timeout(self, done):
        exc = None
        for connect_timeout_sec in (1, .1):
            start = time.time()
            try:
                yield motor.Op(motor.MotorClient(
                    'example.com',
                    port=12345,
                    connectTimeoutMS=1000 * connect_timeout_sec
                ).open)
            except Exception, e:
                exc = e

            self.assertTrue(isinstance(exc, ConnectionFailure))

            connection_duration = time.time() - start
            self.assertTrue(
                abs(connection_duration - connect_timeout_sec) < 0.25, (
                'Expected connection to timeout after about %s sec, timed out'
                ' after %s'
            ) % (connect_timeout_sec, connection_duration))

        done()

    @async_test_engine()
    def test_max_pool_size_validation(self, done):
        cx = motor.MotorClient(host=host, port=port, max_pool_size=-1)
        yield AssertRaises(ConfigurationError, cx.open)

        cx = motor.MotorClient(host=host, port=port, max_pool_size='foo')
        yield AssertRaises(ConfigurationError, cx.open)

        c = motor.MotorClient(host=host, port=port, max_pool_size=100)
        yield motor.Op(c.open)
        self.assertEqual(c.max_pool_size, 100)
        done()

    def test_requests(self):
        cx = self.motor_connection(host, port)
        for method in 'start_request', 'in_request', 'end_request':
            self.assertRaises(NotImplementedError, getattr(cx, method))

    @async_test_engine()
    def test_high_concurrency(self, done):
        self.sync_db.insert_collection.drop()
        self.assertEqual(200, self.sync_coll.count())
        cx = self.motor_connection(host, port).open_sync()
        collection = cx.pymongo_test.test_collection

        concurrency = 100
        ndocs = [0]
        insert_yield_point = yield gen.Callback('insert')

        @gen.engine
        def find(callback):
            cursor = collection.find()
            while (yield cursor.fetch_next):
                cursor.next_object()
                ndocs[0] += 1

                # Part-way through, start an insert
                if ndocs[0] == int((200 * concurrency) / 3):
                    insert(callback=insert_yield_point)
            callback()

        @gen.engine
        def insert(callback):
            for i in range(100):
                yield motor.Op(
                    cx.pymongo_test.insert_collection.insert, {'foo': 'bar'})
            callback()

        for i in range(concurrency):
            find(callback=(yield gen.Callback(i)))

        yield gen.WaitAll(range(concurrency))
        yield gen.Wait('insert')
        self.assertEqual(200 * concurrency, ndocs[0])
        self.assertEqual(100, self.sync_db.insert_collection.count())
        self.sync_db.insert_collection.drop()
        done()


if __name__ == '__main__':
    unittest.main()
