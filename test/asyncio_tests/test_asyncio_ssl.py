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

"""Test AsyncIOMotorClient with SSL."""

import asyncio
import gc
import ssl
import unittest
from unittest import SkipTest

from pymongo.errors import ConfigurationError, ConnectionFailure

import test
from motor.motor_asyncio import AsyncIOMotorClient
from test.asyncio_tests import asyncio_test
from test.test_environment import CA_PEM, CLIENT_PEM, env


# Start a mongod instance like:
#
# mongod \
# --sslOnNormalPorts \
# --sslPEMKeyFile test/certificates/server.pem \
# --sslCAFile     test/certificates/ca.pem
#
# Also, make sure you have 'server' as an alias for localhost in /etc/hosts


class TestAsyncIOSSL(unittest.TestCase):

    def setUp(self):
        if not test.env.server_is_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        asyncio.set_event_loop(None)
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.loop.stop()
        self.loop.run_forever()
        self.loop.close()
        gc.collect()

    def test_config_ssl(self):
        # This test doesn't require a running mongod.
        self.assertRaises(ValueError,
                          AsyncIOMotorClient,
                          io_loop=self.loop,
                          ssl='foo')

        self.assertRaises(ConfigurationError,
                          AsyncIOMotorClient,
                          io_loop=self.loop,
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(IOError, AsyncIOMotorClient,
                          io_loop=self.loop, ssl_certfile="NoFile")

        self.assertRaises(TypeError, AsyncIOMotorClient,
                          io_loop=self.loop, ssl_certfile=True)

        self.assertRaises(IOError, AsyncIOMotorClient,
                          io_loop=self.loop, ssl_keyfile="NoFile")

        self.assertRaises(TypeError, AsyncIOMotorClient,
                          io_loop=self.loop, ssl_keyfile=True)

    @asyncio_test
    async def test_cert_ssl(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(env.host, env.port,
                                    ssl_certfile=CLIENT_PEM,
                                    ssl_ca_certs=CA_PEM,
                                    io_loop=self.loop)

        await client.db.collection.find_one()
        response = await client.admin.command('ismaster')
        if 'setName' in response:
            client = AsyncIOMotorClient(
                env.host, env.port,
                ssl=True,
                ssl_certfile=CLIENT_PEM,
                ssl_ca_certs=CA_PEM,
                replicaSet=response['setName'],
                io_loop=self.loop)

            await client.db.collection.find_one()

    @asyncio_test
    async def test_cert_ssl_validation(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(env.host, env.port,
                                    ssl_certfile=CLIENT_PEM,
                                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                                    ssl_ca_certs=CA_PEM,
                                    io_loop=self.loop)

        await client.db.collection.find_one()
        response = await client.admin.command('ismaster')

        if 'setName' in response:
            client = AsyncIOMotorClient(
                env.host, env.port,
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.loop)

            await client.db.collection.find_one()

    @asyncio_test
    async def test_cert_ssl_validation_none(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(test.env.fake_hostname_uri,
                                    ssl_certfile=CLIENT_PEM,
                                    ssl_cert_reqs=ssl.CERT_NONE,
                                    ssl_ca_certs=CA_PEM,
                                    io_loop=self.loop)

        await client.admin.command('ismaster')

    @asyncio_test
    async def test_cert_ssl_validation_hostname_fail(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(env.host, env.port,
                                    ssl=True, ssl_certfile=CLIENT_PEM,
                                    ssl_ca_certs=CA_PEM,
                                    io_loop=self.loop)

        response = await client.admin.command('ismaster')
        with self.assertRaises(ConnectionFailure):
            # Create client with hostname 'server', not 'localhost',
            # which is what the server cert presents.
            client = AsyncIOMotorClient(test.env.fake_hostname_uri,
                                        serverSelectionTimeoutMS=1000,
                                        ssl_certfile=CLIENT_PEM,
                                        ssl_cert_reqs=ssl.CERT_REQUIRED,
                                        ssl_ca_certs=CA_PEM,
                                        io_loop=self.loop)

            await client.db.collection.find_one()

        if 'setName' in response:
            with self.assertRaises(ConnectionFailure):
                client = AsyncIOMotorClient(
                    test.env.fake_hostname_uri,
                    serverSelectionTimeoutMS=1000,
                    replicaSet=response['setName'],
                    ssl_certfile=CLIENT_PEM,
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_ca_certs=CA_PEM,
                    io_loop=self.loop)

                await client.db.collection.find_one()
