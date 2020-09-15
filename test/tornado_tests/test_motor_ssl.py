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

try:
    import ssl
except ImportError:
    ssl = None

try:
    # Python 2.
    from urllib import quote_plus
except ImportError:
    # Python 3.
    from urllib.parse import quote_plus

from pymongo.errors import ConfigurationError, ConnectionFailure
from tornado.testing import gen_test

import motor
import test
from test import SkipTest
from test.tornado_tests import MotorTest
from test.test_environment import CA_PEM, CLIENT_PEM, env

# Start a mongod instance like:
#
# mongod \
# --sslOnNormalPorts \
# --sslPEMKeyFile test/certificates/server.pem \
# --sslCAFile     test/certificates/ca.pem
#
# Also, make sure you have 'server' as an alias for localhost in /etc/hosts


class MotorSSLTest(MotorTest):
    ssl = True

    def setUp(self):
        if not test.env.server_is_resolvable:
            raise SkipTest("The hostname 'server' must be a localhost alias")

        super().setUp()

    def test_config_ssl(self):
        self.assertRaises(ValueError, motor.MotorClient, ssl='foo')
        self.assertRaises(ConfigurationError,
                          motor.MotorClient,
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(IOError, motor.MotorClient, ssl_certfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_certfile=True)
        self.assertRaises(IOError, motor.MotorClient, ssl_keyfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_keyfile=True)

    @gen_test
    async def test_cert_ssl(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(env.host, env.port,
                                   ssl_certfile=CLIENT_PEM,
                                   ssl_ca_certs=CA_PEM,
                                   io_loop=self.io_loop)

        await client.db.collection.find_one()
        response = await client.admin.command('ismaster')
        if 'setName' in response:
            client = self.motor_rsc(ssl_certfile=CLIENT_PEM,
                                    ssl_ca_certs=CA_PEM)
            await client.db.collection.find_one()

    @gen_test
    async def test_cert_ssl_validation(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            env.host, env.port,
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=CA_PEM,
            io_loop=self.io_loop)

        await client.db.collection.find_one()
        response = await client.admin.command('ismaster')

        if 'setName' in response:
            client = motor.MotorClient(
                env.host, env.port,
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.io_loop)

            await client.db.collection.find_one()

    @gen_test
    async def test_cert_ssl_validation_none(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            test.env.fake_hostname_uri,
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_NONE,
            ssl_ca_certs=CA_PEM,
            io_loop=self.io_loop)

        await client.admin.command('ismaster')

    @gen_test
    async def test_cert_ssl_validation_hostname_fail(self):
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            env.host, env.port,
            ssl_certfile=CLIENT_PEM,
            ssl_ca_certs=CA_PEM,
            io_loop=self.io_loop)

        response = await client.admin.command('ismaster')
        with self.assertRaises(ConnectionFailure):
            # Create client with hostname 'server', not 'localhost',
            # which is what the server cert presents.
            client = motor.MotorClient(
                test.env.fake_hostname_uri,
                serverSelectionTimeoutMS=100,
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.io_loop)

            await client.db.collection.find_one()

        if 'setName' in response:
            with self.assertRaises(ConnectionFailure):
                client = motor.MotorClient(
                    test.env.fake_hostname_uri,
                    serverSelectionTimeoutMS=100,
                    replicaSet=response['setName'],
                    ssl_certfile=CLIENT_PEM,
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_ca_certs=CA_PEM,
                    io_loop=self.io_loop)

                await client.db.collection.find_one()
