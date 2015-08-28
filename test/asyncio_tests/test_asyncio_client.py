# Copyright 2014 MongoDB, Inc.
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

"""Test AsyncIOMotorClient."""
import asyncio
import os
import unittest
from unittest import SkipTest

import pymongo
from pymongo.errors import ConnectionFailure, ConfigurationError

from pymongo.errors import OperationFailure

from motor import motor_asyncio
import test
from test.asyncio_tests import asyncio_test, AsyncIOTestCase, remove_all_users
from test.test_environment import host, port, db_user, db_password
from test.utils import delay


class TestAsyncIOClient(AsyncIOTestCase):
    @asyncio_test
    def test_client_open(self):
        cx = self.asyncio_client()
        self.assertEqual(cx, (yield from cx.open()))
        self.assertEqual(cx, (yield from cx.open()))  # Same the second time.

    @asyncio_test
    def test_client_lazy_connect(self):
        yield from self.db.test_client_lazy_connect.remove()

        # Create client without connecting; connect on demand.
        cx = self.asyncio_client()
        collection = cx.motor_test.test_client_lazy_connect
        future0 = collection.insert({'foo': 'bar'})
        future1 = collection.insert({'foo': 'bar'})
        yield from asyncio.gather(future0, future1, loop=self.loop)
        resp = yield from collection.find({'foo': 'bar'}).count()
        self.assertEqual(2, resp)
        cx.close()

    @asyncio_test
    def test_disconnect(self):
        cx = self.asyncio_client()
        cx.disconnect()
        self.assertEqual(None, cx._get_primary_pool())

    @asyncio_test
    def test_unix_socket(self):
        mongodb_socket = '/tmp/mongodb-27017.sock'

        if not os.access(mongodb_socket, os.R_OK):
            raise SkipTest("Socket file is not accessible")

        uri = 'mongodb://%s' % mongodb_socket
        client = self.asyncio_client(uri)
        collection = client.motor_test.test

        if test.env.auth:
            yield from client.admin.authenticate(db_user, db_password)
        yield from collection.insert({"dummy": "object"})

        # Confirm it fails with a missing socket.
        client = motor_asyncio.AsyncIOMotorClient(
            "mongodb:///tmp/non-existent.sock", io_loop=self.loop)

        with self.assertRaises(ConnectionFailure):
            yield from client.open()
        client.close()

    def test_open_sync(self):
        loop = asyncio.new_event_loop()
        cx = loop.run_until_complete(self.asyncio_client(io_loop=loop).open())
        self.assertTrue(isinstance(cx, motor_asyncio.AsyncIOMotorClient))
        cx.close()
        loop.stop()
        loop.run_forever()
        loop.close()

    def test_database_named_delegate(self):
        self.assertTrue(
            isinstance(self.cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(self.cx['delegate'],
                                   motor_asyncio.AsyncIOMotorDatabase))

    @asyncio_test
    def test_timeout(self):
        # Launch two slow find_ones. The one with a timeout should get an error
        no_timeout_client = self.asyncio_client()
        timeout = self.asyncio_client(socketTimeoutMS=100)
        query = {'$where': delay(0.4), '_id': 1}

        # Need a document, or the $where clause isn't executed.
        test_collection = no_timeout_client.motor_test.test_collection
        yield from test_collection.drop()
        yield from test_collection.insert({'_id': 1})
        timeout_fut = timeout.motor_test.test_collection.find_one(query)
        notimeout_fut = no_timeout_client.motor_test.test_collection.find_one(
            query)

        yield from asyncio.gather(timeout_fut, notimeout_fut,
                                  return_exceptions=True, loop=self.loop)
        self.assertEqual(str(timeout_fut.exception()), 'timed out')
        self.assertEqual({'_id': 1}, notimeout_fut.result())
        no_timeout_client.close()
        timeout.close()

    @asyncio_test
    def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor_asyncio.AsyncIOMotorClient('localhost', 8765,
                                                  io_loop=self.loop)

        with self.assertRaises(ConnectionFailure):
            yield from client.open()

    @asyncio_test(timeout=30)
    def test_connection_timeout(self):
        # Motor merely tries to time out a connection attempt within the
        # specified duration; DNS lookup in particular isn't charged against
        # the timeout. So don't measure how long this takes.
        client = motor_asyncio.AsyncIOMotorClient(
            'example.com', port=12345,
            connectTimeoutMS=1, io_loop=self.loop)

        with self.assertRaises(ConnectionFailure):
            yield from client.open()

    @asyncio_test
    def test_max_pool_size_validation(self):
        with self.assertRaises(ConfigurationError):
            motor_asyncio.AsyncIOMotorClient(max_pool_size=-1,
                                             io_loop=self.loop)

        with self.assertRaises(ConfigurationError):
            motor_asyncio.AsyncIOMotorClient(max_pool_size='foo',
                                             io_loop=self.loop)

        cx = self.asyncio_client(max_pool_size=100)
        self.assertEqual(cx.max_pool_size, 100)
        cx.close()

    @asyncio_test(timeout=60)
    def test_high_concurrency(self):
        return
        yield from self.make_test_data()

        concurrency = 100
        cx = self.asyncio_client(max_pool_size=concurrency)
        expected_finds = 200 * concurrency
        n_inserts = 100

        collection = cx.motor_test.test_collection
        insert_collection = cx.motor_test.insert_collection
        yield from insert_collection.remove()

        ndocs = 0
        insert_future = asyncio.Future(loop=self.loop)

        @asyncio.coroutine
        def find():
            nonlocal ndocs
            cursor = collection.find()
            while (yield from cursor.fetch_next):
                cursor.next_object()
                ndocs += 1

                # Half-way through, start an insert loop
                if ndocs == expected_finds / 2:
                    asyncio.Task(insert(), loop=self.loop)

        @asyncio.coroutine
        def insert():
            for i in range(n_inserts):
                yield from insert_collection.insert({'s': hex(i)})

            insert_future.set_result(None)  # Finished

        yield from asyncio.gather(*[find() for _ in range(concurrency)],
                                  loop=self.loop)
        yield from insert_future
        self.assertEqual(expected_finds, ndocs)
        self.assertEqual(n_inserts, (yield from insert_collection.count()))
        yield from collection.remove()

    @asyncio_test
    def test_drop_database(self):
        # Make sure we can pass an AsyncIOMotorDatabase instance
        # to drop_database
        db = self.cx.test_drop_database
        yield from db.test_collection.insert({})
        names = yield from self.cx.database_names()
        self.assertTrue('test_drop_database' in names)
        yield from self.cx.drop_database(db)
        names = yield from self.cx.database_names()
        self.assertFalse('test_drop_database' in names)

    @asyncio_test
    def test_auth_from_uri(self):
        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # self.db is logged in as root.
        yield from remove_all_users(self.db)
        db = self.db
        try:
            yield from db.add_user(
                'mike', 'password',
                roles=['userAdmin', 'readWrite'])

            client = motor_asyncio.AsyncIOMotorClient(
                'mongodb://u:pass@%s:%d' % (host, port),
                io_loop=self.loop)

            # Note: open() only calls ismaster, doesn't throw auth errors.
            yield from client.open()

            with self.assertRaises(OperationFailure):
                yield from client.db.collection.find_one()

            client = motor_asyncio.AsyncIOMotorClient(
                'mongodb://mike:password@%s:%d/%s' %
                (host, port, db.name),
                io_loop=self.loop)

            yield from client[db.name].collection.find_one()
        finally:
            yield from db.remove_user('mike')

    @asyncio_test
    def test_socketKeepAlive(self):
        # Connect.
        yield from self.cx.server_info()
        ka = self.cx._get_primary_pool()._motor_socket_options.socket_keepalive
        self.assertFalse(ka)

        client = self.asyncio_client(socketKeepAlive=True)
        yield from client.server_info()
        ka = self.cx._get_primary_pool()._motor_socket_options.socket_keepalive
        self.assertFalse(ka)


if __name__ == '__main__':
    unittest.main()
