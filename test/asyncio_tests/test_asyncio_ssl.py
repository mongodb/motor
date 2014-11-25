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

"""Test AsyncIOMotorClient with SSL."""

import ssl
from unittest import SkipTest
from urllib.parse import quote_plus  # The 'parse' submodule is Python 3.

from pymongo.errors import (ConfigurationError,
                            ConnectionFailure,
                            OperationFailure)

from motor.motor_asyncio import (AsyncIOMotorClient,
                                 AsyncIOMotorReplicaSetClient)
import test
from test.asyncio_tests import AsyncIOTestCase, at_least, asyncio_test
from test.test_environment import host, port, CLIENT_PEM, CA_PEM
from test.utils import remove_all_users


# TODO: refactor with test_motor_ssl, probably put in test_environment.
MONGODB_X509_USERNAME = \
    "CN=client,OU=kerneluser,O=10Gen,L=New York City,ST=New York,C=US"

# Start a mongod instance (built with SSL support) from the mongo repository
# checkout:
#
# ./mongod --sslOnNormalPorts
# --sslPEMKeyFile jstests/libs/server.pem \
# --sslCAFile jstests/libs/ca.pem \
# --sslCRLFile jstests/libs/crl.pem
#
# Optionally, also pass --sslWeakCertificateValidation to run test_simple_ssl.
#
# For all tests to pass with AsyncIOReplicaSetClient, the replica set
# configuration must use 'server' for the hostname of all hosts.
# Make sure you have 'server' as an alias for localhost in /etc/hosts.


class TestAsyncIOSSL(AsyncIOTestCase):
    def test_config_ssl(self):
        # This test doesn't require a running mongod.
        self.assertRaises(ConfigurationError,
                          AsyncIOMotorClient,
                          io_loop=self.loop,
                          ssl='foo')

        self.assertRaises(ConfigurationError,
                          AsyncIOMotorClient,
                          io_loop=self.loop,
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(ConfigurationError,
                          AsyncIOMotorReplicaSetClient,
                          io_loop=self.loop,
                          replicaSet='rs',
                          ssl='foo')

        self.assertRaises(ConfigurationError,
                          AsyncIOMotorReplicaSetClient,
                          io_loop=self.loop,
                          replicaSet='rs',
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
    def test_simple_ssl(self):
        if not test.env.mongod_started_with_ssl:
            raise SkipTest("No mongod available over SSL")

        if test.env.mongod_validates_client_cert:
            raise SkipTest("mongod validates SSL certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        # Expects the server to be running with ssl and with
        # no --sslPEMKeyFile or with --sslWeakCertificateValidation.
        client = AsyncIOMotorClient(
            host, port, ssl=True, io_loop=self.loop)

        yield from client.db.collection.find_one()
        response = yield from client.admin.command('ismaster')
        if 'setName' in response:
            client = AsyncIOMotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True,
                io_loop=self.loop)

            yield from client.db.collection.find_one()

    @asyncio_test
    def test_cert_ssl(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not test.env.server_is_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(
            host, port, ssl_certfile=CLIENT_PEM, io_loop=self.loop)

        yield from client.db.collection.find_one()
        response = yield from client.admin.command('ismaster')
        if 'setName' in response:
            client = AsyncIOMotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True,
                ssl_certfile=CLIENT_PEM,
                io_loop=self.loop)

            yield from client.db.collection.find_one()

    @asyncio_test
    def test_cert_ssl_validation(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not test.env.server_is_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=CA_PEM,
            io_loop=self.loop)

        yield from client.db.collection.find_one()
        response = yield from client.admin.command('ismaster')

        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = AsyncIOMotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.loop)

            yield from client.db.collection.find_one()

    @asyncio_test
    def test_cert_ssl_validation_optional(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #
        # Also requires an /etc/hosts entry where "server" is resolvable.
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if not test.env.server_is_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_OPTIONAL,
            ssl_ca_certs=CA_PEM,
            io_loop=self.loop)

        response = yield from client.admin.command('ismaster')
        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = AsyncIOMotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_OPTIONAL,
                ssl_ca_certs=CA_PEM,
                io_loop=self.loop)

            yield from client.db.collection.find_one()

    @asyncio_test
    def test_cert_ssl_validation_hostname_fail(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests e.g.:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        if test.env.auth:
            raise SkipTest("Can't test with auth")

        client = AsyncIOMotorClient(host, port,
                                    ssl=True, ssl_certfile=CLIENT_PEM,
                                    io_loop=self.loop)

        response = yield from client.admin.command('ismaster')
        try:
            # The server presents a certificate named 'server', not localhost.
            client = AsyncIOMotorClient(
                'localhost', port,
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.loop)

            yield from client.db.collection.find_one()
            self.fail("Invalid hostname should have failed")
        except ConnectionFailure as exc:
            self.assertEqual("hostname 'localhost' doesn't match 'server'",
                             str(exc))

        if 'setName' in response:
            try:
                client = AsyncIOMotorReplicaSetClient(
                    '%s:%d' % (host, port),
                    replicaSet=response['setName'],
                    ssl_certfile=CLIENT_PEM,
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_ca_certs=CA_PEM,
                    io_loop=self.loop)

                yield from client.db.collection.find_one()
                self.fail("Invalid hostname should have failed")
            except ConnectionFailure:
                pass

    @asyncio_test
    def test_mongodb_x509_auth(self):
        # Expects the server to be running with the server.pem, ca.pem
        # and crl.pem provided in mongodb and the server tests as well as
        # --auth:
        #
        #   --sslPEMKeyFile=jstests/libs/server.pem
        #   --sslCAFile=jstests/libs/ca.pem
        #   --sslCRLFile=jstests/libs/crl.pem
        #   --auth
        if not test.env.mongod_validates_client_cert:
            raise SkipTest("No mongod available over SSL with certs")

        client = AsyncIOMotorClient(
            host, port, ssl_certfile=CLIENT_PEM, io_loop=self.loop)

        if not (yield from at_least(client, (2, 5, 3, -1))):
            raise SkipTest("MONGODB-X509 tests require MongoDB 2.5.3 or newer")

        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # Give admin all necessary privileges.
        yield from client['$external'].add_user(MONGODB_X509_USERNAME, roles=[
            {'role': 'readWriteAnyDatabase', 'db': 'admin'},
            {'role': 'userAdminAnyDatabase', 'db': 'admin'}])

        collection = client.motor_test.test
        with test.assert_raises(OperationFailure):
            yield from collection.count()

        yield from client.admin.authenticate(
            MONGODB_X509_USERNAME, mechanism='MONGODB-X509')

        yield from collection.remove()
        uri = ('mongodb://%s@%s:%d/?authMechanism='
               'MONGODB-X509' % (
               quote_plus(MONGODB_X509_USERNAME), host, port))

        # SSL options aren't supported in the URI....
        auth_uri_client = AsyncIOMotorClient(
            uri, ssl_certfile=CLIENT_PEM, io_loop=self.loop)

        yield from auth_uri_client.db.collection.find_one()

        # Cleanup.
        yield from remove_all_users(client['$external'])
        yield from client['$external'].logout()
