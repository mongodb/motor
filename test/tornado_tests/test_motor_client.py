# Copyright 2012-2015 MongoDB, Inc.
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

import os
import test
import unittest
from test import SkipTest
from test.test_environment import db_password, db_user, env
from test.tornado_tests import MotorMockServerTest, MotorTest, remove_all_users
from test.utils import get_primary_pool, one

import pymongo
import pymongo.mongo_client
from bson import CodecOptions
from mockupdb import OpQuery
from pymongo import CursorType, ReadPreference, WriteConcern
from pymongo.errors import ConnectionFailure, OperationFailure
from tornado import gen
from tornado.testing import gen_test

import motor


class MotorClientTest(MotorTest):
    @gen_test
    async def test_client_lazy_connect(self):
        await self.db.test_client_lazy_connect.delete_many({})

        # Create client without connecting; connect on demand.
        cx = self.motor_client()
        collection = cx.motor_test.test_client_lazy_connect
        future0 = collection.insert_one({"foo": "bar"})
        future1 = collection.insert_one({"foo": "bar"})
        await gen.multi([future0, future1])

        self.assertEqual(2, (await collection.count_documents({"foo": "bar"})))

        cx.close()

    @gen_test
    async def test_unix_socket(self):
        if env.mongod_started_with_ssl:
            raise SkipTest("Server started with SSL")

        mongodb_socket = "/tmp/mongodb-%d.sock" % env.port
        if not os.access(mongodb_socket, os.R_OK):
            raise SkipTest("Socket file is not accessible")

        encoded_socket = "%2Ftmp%2Fmongodb-" + str(env.port) + ".sock"
        if test.env.auth:
            uri = "mongodb://%s:%s@%s" % (db_user, db_password, encoded_socket)
        else:
            uri = "mongodb://%s" % (encoded_socket,)

        client = self.motor_client(uri)
        await client.motor_test.test.insert_one({"dummy": "object"})

        # Confirm it fails with a missing socket.
        client = motor.MotorClient(
            "mongodb://%2Ftmp%2Fnon-existent.sock",
            io_loop=self.io_loop,
            serverSelectionTimeoutMS=100,
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")

    def test_io_loop(self):
        with self.assertRaises(TypeError):
            motor.MotorClient(test.env.uri, io_loop="foo")

    def test_database_named_delegate(self):
        self.assertTrue(isinstance(self.cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(self.cx["delegate"], motor.MotorDatabase))

    @gen_test
    async def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor.MotorClient(
            "localhost", 8765, io_loop=self.io_loop, serverSelectionTimeoutMS=10
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")

    @gen_test(timeout=30)
    async def test_connection_timeout(self):
        # Motor merely tries to time out a connection attempt within the
        # specified duration; DNS lookup in particular isn't charged against
        # the timeout. So don't measure how long this takes.
        client = motor.MotorClient(
            "example.com", port=12345, serverSelectionTimeoutMS=1, io_loop=self.io_loop
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")

    def test_max_pool_size_validation(self):
        with self.assertRaises(ValueError):
            motor.MotorClient(maxPoolSize=-1)

        with self.assertRaises(ValueError):
            motor.MotorClient(maxPoolSize="foo")

        cx = self.motor_client(maxPoolSize=100)
        self.assertEqual(cx.options.pool_options.max_pool_size, 100)
        cx.close()

    @gen_test(timeout=30)
    async def test_drop_database(self):
        # Make sure we can pass a MotorDatabase instance to drop_database
        db = self.cx.test_drop_database
        await db.test_collection.insert_one({})
        names = await self.cx.list_database_names()
        self.assertTrue("test_drop_database" in names)
        await self.cx.drop_database(db)
        names = await self.cx.list_database_names()
        self.assertFalse("test_drop_database" in names)

    @gen_test
    async def test_auth_from_uri(self):
        if not test.env.auth:
            raise SkipTest("Authentication is not enabled on server")

        # self.db is logged in as root.
        await remove_all_users(self.db)
        db = self.db
        try:
            test.env.create_user(db.name, "mike", "password", roles=["userAdmin", "readWrite"])

            client = self.motor_client("mongodb://u:pass@%s:%d" % (env.host, env.port))

            with self.assertRaises(OperationFailure):
                await client.db.collection.find_one()

            client = self.motor_client(
                "mongodb://mike:password@%s:%d/%s" % (env.host, env.port, db.name)
            )

            await client[db.name].collection.find_one()
        finally:
            test.env.drop_user(db.name, "mike")

    def test_get_database(self):
        codec_options = CodecOptions(tz_aware=True)
        write_concern = WriteConcern(w=2, j=True)
        db = self.cx.get_database("foo", codec_options, ReadPreference.SECONDARY, write_concern)

        self.assertTrue(isinstance(db, motor.MotorDatabase))
        self.assertEqual("foo", db.name)
        self.assertEqual(codec_options, db.codec_options)
        self.assertEqual(ReadPreference.SECONDARY, db.read_preference)
        self.assertEqual(write_concern, db.write_concern)

    @gen_test
    async def test_list_databases(self):
        await self.collection.insert_one({})
        cursor = await self.cx.list_databases()
        self.assertIsInstance(cursor, motor.motor_tornado.MotorCommandCursor)

        # Make sure the cursor works, by searching for "local" database.
        while await cursor.fetch_next:
            info = cursor.next_object()
            if info["name"] == self.collection.database.name:
                break
        else:
            self.fail("'%s' database not found" % self.collection.database.name)

    @gen_test
    async def test_list_database_names(self):
        await self.collection.insert_one({})
        names = await self.cx.list_database_names()
        self.assertIsInstance(names, list)
        self.assertIn(self.collection.database.name, names)


class MotorClientTimeoutTest(MotorMockServerTest):
    @gen_test
    async def test_timeout(self):
        server = self.server(auto_ismaster=True)
        client = motor.MotorClient(server.uri, socketTimeoutMS=100)

        with self.assertRaises(pymongo.errors.AutoReconnect) as context:
            await client.motor_test.test_collection.find_one()

        self.assertIn("timed out", str(context.exception))
        client.close()


class MotorClientExhaustCursorTest(MotorMockServerTest):
    def primary_server(self):
        primary = self.server()
        hosts = [primary.address_string]
        primary.autoresponds("ismaster", ismaster=True, setName="rs", hosts=hosts, maxWireVersion=6)

        return primary

    def primary_or_standalone(self, rs):
        if rs:
            return self.primary_server()
        else:
            return self.server(auto_ismaster=True)

    async def _test_exhaust_query_server_error(self, rs):
        # When doing an exhaust query, the socket stays checked out on success
        # but must be checked in on error to avoid counter leak.
        server = self.primary_or_standalone(rs=rs)
        client = motor.MotorClient(server.uri, maxPoolSize=1)
        await client.admin.command("ismaster")
        pool = get_primary_pool(client)
        sock_info = one(pool.sockets)
        cursor = client.db.collection.find(cursor_type=CursorType.EXHAUST)

        # With Tornado, simply accessing fetch_next starts the fetch.
        fetch_next = cursor.fetch_next
        request = await self.run_thread(server.receives, OpQuery)
        request.fail()

        with self.assertRaises(pymongo.errors.OperationFailure):
            await fetch_next

        self.assertFalse(sock_info.closed)
        self.assertEqual(sock_info, one(pool.sockets))

    @gen_test
    async def test_exhaust_query_server_error_standalone(self):
        await self._test_exhaust_query_server_error(rs=False)

    @gen_test
    async def test_exhaust_query_server_error_rs(self):
        await self._test_exhaust_query_server_error(rs=True)

    async def _test_exhaust_query_network_error(self, rs):
        # When doing an exhaust query, the socket stays checked out on success
        # but must be checked in on error to avoid counter leak.
        server = self.primary_or_standalone(rs=rs)
        client = motor.MotorClient(server.uri, maxPoolSize=1, retryReads=False)

        await client.admin.command("ismaster")
        pool = get_primary_pool(client)
        pool._check_interval_seconds = None  # Never check.
        sock_info = one(pool.sockets)

        cursor = client.db.collection.find(cursor_type=CursorType.EXHAUST)

        # With Tornado, simply accessing fetch_next starts the fetch.
        fetch_next = cursor.fetch_next
        request = await self.run_thread(server.receives, OpQuery)
        request.hangs_up()

        with self.assertRaises(pymongo.errors.ConnectionFailure):
            await fetch_next

        self.assertTrue(sock_info.closed)
        del cursor
        self.assertNotIn(sock_info, pool.sockets)

    @gen_test
    async def test_exhaust_query_network_error_standalone(self):
        await self._test_exhaust_query_network_error(rs=False)

    @gen_test
    async def test_exhaust_query_network_error_rs(self):
        await self._test_exhaust_query_network_error(rs=True)


class MotorClientHandshakeTest(MotorMockServerTest):
    @gen_test
    async def test_handshake(self):
        server = self.server()
        client = motor.MotorClient(server.uri, connectTimeoutMS=100, serverSelectionTimeoutMS=100)

        # Trigger connection.
        future = client.db.command("ping")
        ismaster = await self.run_thread(server.receives, "ismaster")
        meta = ismaster.doc["client"]
        self.assertEqual("PyMongo|Motor", meta["driver"]["name"])
        self.assertIn("Tornado", meta["platform"])
        self.assertTrue(
            meta["driver"]["version"].endswith(motor.version),
            "Version in handshake [%s] doesn't end with Motor version [%s]"
            % (meta["driver"]["version"], motor.version),
        )

        ismaster.hangs_up()
        server.stop()
        client.close()
        try:
            await future
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
