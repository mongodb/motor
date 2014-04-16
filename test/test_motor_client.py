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

import os
import socket
import unittest
import sys

import pymongo
from pymongo.errors import ConfigurationError, OperationFailure
from pymongo.errors import ConnectionFailure
from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.testing import gen_test, netutil

import motor
import test
from test import host, port, assert_raises, MotorTest, setUpModule, SkipTest
from test.motor_client_test_generic import MotorClientTestMixin
from test.utils import server_started_with_auth, remove_all_users, delay


class MotorClientTest(MotorTest):
    @gen_test
    def test_client_open(self):
        cx = motor.MotorClient(host, port, io_loop=self.io_loop)
        self.assertEqual(cx, (yield cx.open()))
        self.assertEqual(cx, (yield cx.open()))  # Same the second time.

    @gen_test
    def test_client_lazy_connect(self):
        test.sync_cx.motor_test.test_client_lazy_connect.remove()

        # Create client without connecting; connect on demand.
        cx = motor.MotorClient(host, port, io_loop=self.io_loop)
        collection = cx.motor_test.test_client_lazy_connect
        future0 = collection.insert({'foo': 'bar'})
        future1 = collection.insert({'foo': 'bar'})
        yield [future0, future1]

        self.assertEqual(2, (yield collection.find({'foo': 'bar'}).count()))

        cx.close()

    @gen_test
    def test_disconnect(self):
        cx = self.motor_client()
        cx.disconnect()
        self.assertEqual(None, cx._get_primary_pool())

    @gen_test
    def test_unix_socket(self):
        if not hasattr(socket, "AF_UNIX"):
            raise SkipTest("UNIX-sockets are not supported on this system")

        if (sys.platform == 'darwin' and
                (yield server_started_with_auth(self.cx))):
            raise SkipTest("SERVER-8492")

        mongodb_socket = '/tmp/mongodb-27017.sock'
        if not os.access(mongodb_socket, os.R_OK):
            raise SkipTest("Socket file is not accessible")

        yield motor.MotorClient(
            "mongodb://%s" % mongodb_socket, io_loop=self.io_loop).open()

        client = yield motor.MotorClient(
            "mongodb://%s" % mongodb_socket, io_loop=self.io_loop).open()

        yield client.motor_test.test.save({"dummy": "object"})

        # Confirm we can read via the socket.
        dbs = yield client.database_names()
        self.assertTrue("motor_test" in dbs)
        client.close()

        # Confirm it fails with a missing socket.
        client = motor.MotorClient(
            "mongodb:///tmp/non-existent.sock", io_loop=self.io_loop)

        with assert_raises(ConnectionFailure):
            yield client.open()

    def test_io_loop(self):
        with assert_raises(TypeError):
            motor.MotorClient(host, port, io_loop='foo')

    def test_open_sync(self):
        loop = IOLoop()
        cx = loop.run_sync(motor.MotorClient(host, port, io_loop=loop).open)
        self.assertTrue(isinstance(cx, motor.MotorClient))

    def test_database_named_delegate(self):
        self.assertTrue(
            isinstance(self.cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(self.cx['delegate'], motor.MotorDatabase))

    @gen_test
    def test_timeout(self):
        # Launch two slow find_ones. The one with a timeout should get an error
        no_timeout = self.motor_client()
        timeout = self.motor_client(host, port, socketTimeoutMS=100)
        query = {'$where': delay(0.5), '_id': 1}

        # Need a document, or the $where clause isn't executed.
        yield no_timeout.motor_test.test_collection.insert({'_id': 1})
        timeout_fut = timeout.motor_test.test_collection.find_one(query)
        notimeout_fut = no_timeout.motor_test.test_collection.find_one(query)

        error = None
        try:
            yield [timeout_fut, notimeout_fut]
        except pymongo.errors.AutoReconnect as e:
            error = e

        self.assertEqual(str(error), 'timed out')
        self.assertEqual({'_id': 1}, notimeout_fut.result())
        no_timeout.close()
        timeout.close()

    @gen_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorClient('localhost', 8765, io_loop=self.io_loop)

        # Test the Future interface.
        with assert_raises(ConnectionFailure):
            yield client.open()

        # Test with a callback.
        (result, error), _ = yield gen.Task(client.open)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, ConnectionFailure))

    @gen_test
    def test_connection_timeout(self):
        # Motor merely tries to time out a connection attempt within the
        # specified duration; DNS lookup in particular isn't charged against
        # the timeout. So don't measure how long this takes.
        client = motor.MotorClient(
            'example.com', port=12345,
            connectTimeoutMS=1, io_loop=self.io_loop)

        with assert_raises(ConnectionFailure):
            yield client.open()

    @gen_test
    def test_max_pool_size_validation(self):
        with assert_raises(ConfigurationError):
            motor.MotorClient(host=host, port=port, max_pool_size=-1)

        with assert_raises(ConfigurationError):
            motor.MotorClient(host=host, port=port, max_pool_size='foo')

        cx = motor.MotorClient(
            host=host, port=port, max_pool_size=100, io_loop=self.io_loop)

        self.assertEqual(cx.max_pool_size, 100)
        cx.close()

    @gen_test
    def test_high_concurrency(self):
        yield self.make_test_data()

        concurrency = 100
        cx = self.motor_client(max_pool_size=concurrency)
        test.sync_db.insert_collection.drop()
        self.assertEqual(200, test.sync_collection.count())
        expected_finds = 200 * concurrency
        n_inserts = 100

        collection = cx.motor_test.test_collection
        insert_collection = cx.motor_test.insert_collection

        ndocs = [0]
        insert_future = Future()

        @gen.coroutine
        def find():
            cursor = collection.find()
            while (yield cursor.fetch_next):
                cursor.next_object()
                ndocs[0] += 1

                # Half-way through, start an insert loop
                if ndocs[0] == expected_finds / 2:
                    insert()

        @gen.coroutine
        def insert():
            for i in range(n_inserts):
                yield insert_collection.insert({'s': hex(i)})

            insert_future.set_result(None)  # Finished

        yield [find() for _ in range(concurrency)]
        yield insert_future
        self.assertEqual(expected_finds, ndocs[0])
        self.assertEqual(n_inserts, test.sync_db.insert_collection.count())
        test.sync_db.insert_collection.drop()

    @gen_test
    def test_drop_database(self):
        # Make sure we can pass a MotorDatabase instance to drop_database
        db = self.cx.test_drop_database
        yield db.test_collection.insert({})
        names = yield self.cx.database_names()
        self.assertTrue('test_drop_database' in names)
        yield self.cx.drop_database(db)
        names = yield self.cx.database_names()
        self.assertFalse('test_drop_database' in names)

    @gen_test
    def test_auth_from_uri(self):
        if not (yield server_started_with_auth(self.cx)):
            raise SkipTest('Authentication is not enabled on server')

        yield remove_all_users(self.db)
        yield remove_all_users(self.cx.admin)
        yield self.cx.admin.add_user('admin', 'pass')
        yield self.cx.admin.authenticate('admin', 'pass')

        db = self.db
        try:
            yield db.add_user(
                'mike', 'password',
                roles=['userAdmin', 'readWrite'])

            client = motor.MotorClient('mongodb://foo:bar@%s:%d' % (host, port))

            # Note: open() only calls ismaster, doesn't throw auth errors.
            yield client.open()

            with assert_raises(OperationFailure):
                yield client.db.collection.find_one()

            client.close()

            client = motor.MotorClient(
                'mongodb://user:pass@%s:%d/%s' %
                (host, port, db.name))

            yield client.open()
            client.close()

            client = motor.MotorClient(
                'mongodb://mike:password@%s:%d/%s' %
                (host, port, db.name))

            yield client[db.name].collection.find_one()
            client.close()

        finally:
            yield db.remove_user('mike')
            yield self.cx.admin.remove_user('admin')


class MotorResolverTest(MotorTest):
    nonexistent_domain = 'doesntexist'

    def setUp(self):
        super(MotorResolverTest, self).setUp()

        # Caching the lookup helps prevent timeouts, at least on Mac OS.
        try:
            socket.getaddrinfo(self.nonexistent_domain, port)
        except socket.gaierror:
            pass

    # Helper method.
    @gen.coroutine
    def test_resolver(self, resolver_name):
        config = netutil.Resolver._save_configuration()
        try:
            netutil.Resolver.configure(resolver_name)
            client = motor.MotorClient(host, port, io_loop=self.io_loop)
            yield client.open()  # No error.

            with assert_raises(pymongo.errors.ConnectionFailure):
                client = motor.MotorClient(
                    self.nonexistent_domain,
                    connectTimeoutMS=100,
                    io_loop=self.io_loop)

                yield client.open()

        finally:
            netutil.Resolver._restore_configuration(config)

    test_resolver.__test__ = False

    @gen_test
    def test_blocking_resolver(self):
        yield self.test_resolver('tornado.netutil.BlockingResolver')

    @gen_test
    def test_threaded_resolver(self):
        try:
            import concurrent.futures
        except ImportError:
            raise SkipTest('concurrent.futures module not available')

        yield self.test_resolver('tornado.netutil.ThreadedResolver')

    @gen_test
    def test_twisted_resolver(self):
        try:
            import twisted
        except ImportError:
            raise SkipTest('Twisted not installed')
        yield self.test_resolver('tornado.platform.twisted.TwistedResolver')

    @gen_test(timeout=30)
    def test_cares_resolver(self):
        try:
            import pycares
        except ImportError:
            raise SkipTest('pycares not installed')
        yield self.test_resolver(
            'tornado.platform.caresresolver.CaresResolver')


class MotorClientTestGeneric(MotorClientTestMixin, MotorTest):
    def get_client(self):
        return self.cx


if __name__ == '__main__':
    unittest.main()
