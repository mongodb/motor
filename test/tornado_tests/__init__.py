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

"""Utilities for testing Motor with Tornado."""

import concurrent.futures
import functools
from test.test_environment import CA_PEM, CLIENT_PEM, env
from test.version import Version
from unittest import SkipTest

from bson import SON
from mockupdb import MockupDB
from tornado import testing

import motor


async def get_command_line(client):
    command_line = await client.admin.command("getCmdLineOpts")
    assert command_line["ok"] == 1, "getCmdLineOpts() failed"
    return command_line


async def server_is_mongos(client):
    ismaster_response = await client.admin.command("ismaster")
    return ismaster_response.get("msg") == "isdbgrid"


async def skip_if_mongos(client):
    is_mongos = await server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


async def remove_all_users(db):
    await db.command({"dropAllUsersFromDatabase": 1})


class MotorTest(testing.AsyncTestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super().setUp()

        if self.ssl and not env.mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        self.cx = self.motor_client()
        self.db = self.cx.motor_test
        self.collection = self.db.test_collection

    async def make_test_data(self):
        await self.collection.delete_many({})
        await self.collection.insert_many([{"_id": i} for i in range(200)])

    make_test_data.__test__ = False

    async def set_fail_point(self, client, command_args):
        cmd = SON([("configureFailPoint", "failCommand")])
        cmd.update(command_args)
        await client.admin.command(cmd)

    def get_client_kwargs(self, **kwargs):
        if env.mongod_started_with_ssl:
            kwargs.setdefault("tlsCAFile", CA_PEM)
            kwargs.setdefault("tlsCertificateKeyFile", CLIENT_PEM)

        kwargs.setdefault("tls", env.mongod_started_with_ssl)
        kwargs.setdefault("io_loop", self.io_loop)

        return kwargs

    def motor_client(self, uri=None, *args, **kwargs):
        """Get a MotorClient.

        Ignores self.ssl, you must pass 'ssl' argument. You'll probably need to
        close the client to avoid file-descriptor problems after AsyncTestCase
        calls self.io_loop.close(all_fds=True).
        """
        return motor.MotorClient(uri or env.uri, *args, **self.get_client_kwargs(**kwargs))

    def motor_rsc(self, uri=None, *args, **kwargs):
        """Get an open MotorClient for replica set.

        Ignores self.ssl, you must pass 'ssl' argument.
        """
        return motor.MotorClient(uri or env.rs_uri, *args, **self.get_client_kwargs(**kwargs))

    def tearDown(self):
        env.sync_cx.motor_test.test_collection.delete_many({})
        self.cx.close()
        super().tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super().setUp()
        if not env.is_replica_set:
            raise SkipTest("Not connected to a replica set")

        self.rsc = self.motor_rsc()


class MotorMockServerTest(MotorTest):

    executor = concurrent.futures.ThreadPoolExecutor(1)

    def server(self, *args, **kwargs):
        server = MockupDB(*args, **kwargs)
        server.run()
        self.addCleanup(server.stop)
        return server

    def client_server(self, *args, **kwargs):
        server = self.server(*args, **kwargs)
        client = motor.motor_tornado.MotorClient(server.uri, io_loop=self.io_loop)

        self.addCleanup(client.close)
        return client, server

    async def run_thread(self, fn, *args, **kwargs):
        return await self.io_loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))


class AsyncVersion(Version):
    """Version class that can be instantiated with an async client from
    within a coroutine."""

    @classmethod
    async def from_client(cls, client):
        info = await client.server_info()
        if "versionArray" in info:
            return cls.from_version_array(info["versionArray"])
        return cls.from_string(info["version"])
