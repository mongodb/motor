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

try:
    import contextvars
except ImportError:
    contextvars = False


import test
from test.asyncio_tests import (
    AsyncIOMockServerTestCase,
    AsyncIOTestCase,
    asyncio_test,
    remove_all_users,
)
from test.test_environment import db_password, db_user, env
from test.utils import get_primary_pool

import pymongo
from bson import CodecOptions
from pymongo import ReadPreference, WriteConcern, monitoring
from pymongo.errors import ConnectionFailure, OperationFailure

import motor
from motor import motor_asyncio


class TestAsyncIOClient(AsyncIOTestCase):
    @asyncio_test
    async def test_client_lazy_connect(self):
        await self.db.test_client_lazy_connect.delete_many({})

        # Create client without connecting; connect on demand.
        cx = self.asyncio_client()
        collection = cx.motor_test.test_client_lazy_connect
        future0 = collection.insert_one({"foo": "bar"})
        future1 = collection.insert_one({"foo": "bar"})
        await asyncio.gather(future0, future1)
        resp = await collection.count_documents({"foo": "bar"})
        self.assertEqual(2, resp)
        cx.close()

    @asyncio_test
    async def test_close(self):
        cx = self.asyncio_client()
        cx.close()
        self.assertEqual(None, get_primary_pool(cx))

    @asyncio_test
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

        client = self.asyncio_client(uri)
        collection = client.motor_test.test
        await collection.insert_one({"dummy": "object"})

        # Confirm it fails with a missing socket.
        client = motor_asyncio.AsyncIOMotorClient(
            "mongodb://%2Ftmp%2Fnon-existent.sock", io_loop=self.loop, serverSelectionTimeoutMS=100
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")
        client.close()

    def test_database_named_delegate(self):
        self.assertTrue(isinstance(self.cx.delegate, pymongo.mongo_client.MongoClient))
        self.assertTrue(isinstance(self.cx["delegate"], motor_asyncio.AsyncIOMotorDatabase))

    @asyncio_test
    async def test_reconnect_in_case_connection_closed_by_mongo(self):
        cx = self.asyncio_client(maxPoolSize=1, retryReads=False)
        await cx.admin.command("ping")

        # close motor_socket, we imitate that connection to mongo server
        # lost, as result we should have AutoReconnect instead of
        # IncompleteReadError
        pool = get_primary_pool(cx)
        socket = pool.sockets.pop()
        socket.sock.close()
        pool.sockets.appendleft(socket)

        with self.assertRaises(pymongo.errors.AutoReconnect):
            await cx.motor_test.test_collection.find_one()

    @asyncio_test
    async def test_connection_failure(self):
        # Assuming there isn't anything actually running on this port
        client = motor_asyncio.AsyncIOMotorClient(
            "localhost", 8765, serverSelectionTimeoutMS=10, io_loop=self.loop
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")

    @asyncio_test(timeout=30)
    async def test_connection_timeout(self):
        # Motor merely tries to time out a connection attempt within the
        # specified duration; DNS lookup in particular isn't charged against
        # the timeout. So don't measure how long this takes.
        client = motor_asyncio.AsyncIOMotorClient(
            "example.com", port=12345, serverSelectionTimeoutMS=1, io_loop=self.loop
        )

        with self.assertRaises(ConnectionFailure):
            await client.admin.command("ismaster")

    @asyncio_test
    async def test_max_pool_size_validation(self):
        with self.assertRaises(ValueError):
            motor_asyncio.AsyncIOMotorClient(maxPoolSize=-1, io_loop=self.loop)

        with self.assertRaises(ValueError):
            motor_asyncio.AsyncIOMotorClient(maxPoolSize="foo", io_loop=self.loop)

        cx = self.asyncio_client(maxPoolSize=100)
        self.assertEqual(cx.options.pool_options.max_pool_size, 100)
        cx.close()

    @asyncio_test(timeout=30)
    async def test_drop_database(self):
        # Make sure we can pass an AsyncIOMotorDatabase instance
        # to drop_database
        db = self.cx.test_drop_database
        await db.test_collection.insert_one({})
        names = await self.cx.list_database_names()
        self.assertTrue("test_drop_database" in names)
        await self.cx.drop_database(db)
        names = await self.cx.list_database_names()
        self.assertFalse("test_drop_database" in names)

    @asyncio_test
    async def test_auth_from_uri(self):
        if not test.env.auth:
            raise SkipTest("Authentication is not enabled on server")

        # self.db is logged in as root.
        await remove_all_users(self.db)
        db = self.db
        try:
            test.env.create_user(db.name, "mike", "password", roles=["userAdmin", "readWrite"])

            client = self.asyncio_client("mongodb://u:pass@%s:%d" % (env.host, env.port))

            with self.assertRaises(OperationFailure):
                await client.db.collection.find_one()

            client = self.asyncio_client(
                "mongodb://mike:password@%s:%d/%s" % (env.host, env.port, db.name)
            )

            await client[db.name].collection.find_one()
        finally:
            test.env.drop_user(db.name, "mike")

    def test_get_database(self):
        codec_options = CodecOptions(tz_aware=True)
        write_concern = WriteConcern(w=2, j=True)
        db = self.cx.get_database("foo", codec_options, ReadPreference.SECONDARY, write_concern)

        assert isinstance(db, motor_asyncio.AsyncIOMotorDatabase)
        self.assertEqual("foo", db.name)
        self.assertEqual(codec_options, db.codec_options)
        self.assertEqual(ReadPreference.SECONDARY, db.read_preference)
        self.assertEqual(write_concern, db.write_concern)

    @asyncio_test
    async def test_list_databases(self):
        await self.collection.insert_one({})
        cursor = await self.cx.list_databases()
        self.assertIsInstance(cursor, motor_asyncio.AsyncIOMotorCommandCursor)

        while await cursor.fetch_next:
            info = cursor.next_object()
            if info["name"] == self.collection.database.name:
                break
        else:
            self.fail("'%s' database not found" % self.collection.database.name)

    @asyncio_test
    async def test_list_database_names(self):
        await self.collection.insert_one({})
        names = await self.cx.list_database_names()
        self.assertIsInstance(names, list)
        self.assertIn(self.collection.database.name, names)

    @unittest.skipIf(not contextvars, "this test requires contextvars")
    @asyncio_test
    async def test_contextvars_support(self):
        var = contextvars.ContextVar("variable", default="default")

        class Listener(monitoring.CommandListener):
            def __init__(self):
                self.values = []

            def save_contextvar_value(self):
                self.values.append(var.get())

            def started(self, event):
                self.save_contextvar_value()

            def succeeded(self, event):
                self.save_contextvar_value()

            def failed(self, event):
                pass

        listener = Listener()
        client = self.asyncio_client(event_listeners=[listener])
        coll = client[self.db.name].test

        await coll.insert_one({})
        self.assertTrue(listener.values)
        for val in listener.values:
            self.assertEqual(val, "default")

        var.set("ContextVar value")
        listener.values.clear()

        await coll.insert_one({})
        self.assertTrue(listener.values)
        for val in listener.values:
            self.assertEqual(val, "ContextVar value")


class TestAsyncIOClientTimeout(AsyncIOMockServerTestCase):
    @asyncio_test
    async def test_timeout(self):
        server = self.server(auto_ismaster=True)
        client = motor_asyncio.AsyncIOMotorClient(
            server.uri, socketTimeoutMS=100, io_loop=self.loop
        )

        with self.assertRaises(pymongo.errors.AutoReconnect) as context:
            await client.motor_test.test_collection.find_one()

        self.assertIn("timed out", str(context.exception))
        client.close()


class TestAsyncIOClientHandshake(AsyncIOMockServerTestCase):
    @asyncio_test
    async def test_handshake(self):
        server = self.server()
        client = motor_asyncio.AsyncIOMotorClient(
            server.uri, connectTimeoutMS=100, serverSelectionTimeoutMS=100
        )

        # Trigger connection.
        future = client.db.command("ping")
        ismaster = await self.run_thread(server.receives, "ismaster")
        meta = ismaster.doc["client"]
        self.assertEqual("PyMongo|Motor", meta["driver"]["name"])
        # AsyncIOMotorClient adds nothing to platform.
        self.assertNotIn("Tornado", meta["platform"])
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
