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

import socket
import ssl

try:
    # Python 2.
    from urllib import quote_plus
except ImportError:
    # Python 3.
    from urllib.parse import quote_plus

from pymongo.common import HAS_SSL
from pymongo.errors import (ConfigurationError,
                            ConnectionFailure,
                            OperationFailure)
from tornado.testing import gen_test

import motor
import test
from test import MotorTest, host, port, version, SkipTest
from test import CLIENT_PEM, CA_PEM
from test.utils import remove_all_users


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
# For all tests to pass with MotorReplicaSetClient, the replica set
# configuration must use 'server' for the hostname of all hosts.
# Make sure you have 'server' as an alias for localhost in /etc/hosts.


class MotorNoSSLTest(MotorTest):
    ssl = True

    def test_no_ssl(self):
        # Test that ConfigurationError is raised if the ssl
        # module isn't available.
        if HAS_SSL:
            raise SkipTest(
                "We have SSL compiled into Python, can't test what happens "
                "without SSL")

        # ssl=True is passed explicitly.
        self.assertRaises(ConfigurationError,
                          motor.MotorClient, ssl=True)
        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl=True)

        # ssl=True is implied.
        self.assertRaises(ConfigurationError,
                          motor.MotorClient,
                          ssl_certfile=CLIENT_PEM)
        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl_certfile=CLIENT_PEM)


class MotorSSLTest(MotorTest):
    ssl = True

    def setUp(self):
        if not HAS_SSL:
            raise SkipTest("The ssl module is not available.")

        super(MotorSSLTest, self).setUp()

    def test_config_ssl(self):
        self.assertRaises(ConfigurationError, motor.MotorClient, ssl='foo')
        self.assertRaises(ConfigurationError,
                          motor.MotorClient,
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl='foo')

        self.assertRaises(ConfigurationError,
                          motor.MotorReplicaSetClient,
                          replicaSet='rs',
                          ssl=False,
                          ssl_certfile=CLIENT_PEM)

        self.assertRaises(IOError, motor.MotorClient, ssl_certfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_certfile=True)
        self.assertRaises(IOError, motor.MotorClient, ssl_keyfile="NoFile")
        self.assertRaises(TypeError, motor.MotorClient, ssl_keyfile=True)

    @gen_test
    def test_simple_ssl(self):
        if test.env.mongod_validates_client_cert:
            raise SkipTest("mongod validates SSL certs")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        # Expects the server to be running with ssl and with
        # no --sslPEMKeyFile or with --sslWeakCertificateValidation.
        client = motor.MotorClient(host, port, ssl=True, io_loop=self.io_loop)
        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            client = motor.MotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True,
                io_loop=self.io_loop)

            yield client.db.collection.find_one()

    @gen_test
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

        if not test.env.is_server_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            host, port, ssl_certfile=CLIENT_PEM, io_loop=self.io_loop)

        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            client = motor.MotorReplicaSetClient(
                '%s:%d' % (host, port),
                replicaSet=response['setName'],
                ssl=True,
                ssl_certfile=CLIENT_PEM,
                io_loop=self.io_loop)

            yield client.db.collection.find_one()

    @gen_test
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

        if not test.env.is_server_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=CA_PEM,
            io_loop=self.io_loop)

        yield client.db.collection.find_one()
        response = yield client.admin.command('ismaster')

        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = motor.MotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.io_loop)

            yield client.db.collection.find_one()

    @gen_test
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

        if not test.env.is_server_resolvable:
            raise SkipTest("No hosts entry for 'server'. Cannot validate "
                           "hostname in the certificate")

        if test.env.auth:
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            'server',
            ssl_certfile=CLIENT_PEM,
            ssl_cert_reqs=ssl.CERT_OPTIONAL,
            ssl_ca_certs=CA_PEM,
            io_loop=self.io_loop)

        response = yield client.admin.command('ismaster')
        if 'setName' in response:
            if response['primary'].split(":")[0] != 'server':
                raise SkipTest("No hosts in the replicaset for 'server'. "
                               "Cannot validate hostname in the certificate")

            client = motor.MotorReplicaSetClient(
                'server',
                replicaSet=response['setName'],
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_OPTIONAL,
                ssl_ca_certs=CA_PEM,
                io_loop=self.io_loop)

            yield client.db.collection.find_one()

    @gen_test
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
            raise SkipTest("can't test with auth")

        client = motor.MotorClient(
            host, port,
            ssl_certfile=CLIENT_PEM,
            io_loop=self.io_loop)

        response = yield client.admin.command('ismaster')
        try:
            # Create client with hostname 'localhost' or whatever, not
            # the name 'server', which is what the server cert presents.
            client = motor.MotorClient(
                host, port,
                ssl_certfile=CLIENT_PEM,
                ssl_cert_reqs=ssl.CERT_REQUIRED,
                ssl_ca_certs=CA_PEM,
                io_loop=self.io_loop)

            yield client.db.collection.find_one()
            self.fail("Invalid hostname should have failed")
        except ConnectionFailure:
            pass

        if 'setName' in response:
            try:
                client = motor.MotorReplicaSetClient(
                    '%s:%d' % (host, port),
                    replicaSet=response['setName'],
                    ssl_certfile=CLIENT_PEM,
                    ssl_cert_reqs=ssl.CERT_REQUIRED,
                    ssl_ca_certs=CA_PEM,
                    io_loop=self.io_loop)

                yield client.db.collection.find_one()
                self.fail("Invalid hostname should have failed")
            except ConnectionFailure:
                pass

    @gen_test
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

        client = motor.MotorClient(
            host, port, ssl_certfile=CLIENT_PEM, io_loop=self.io_loop)

        if not (yield version.at_least(client, (2, 5, 3, -1))):
            raise SkipTest("MONGODB-X509 tests require MongoDB 2.5.3 or newer")

        if not test.env.auth:
            raise SkipTest('Authentication is not enabled on server')

        # Give admin all necessary privileges.
        test.env.sync_cx['$external'].add_user(MONGODB_X509_USERNAME, roles=[
            {'role': 'readWriteAnyDatabase', 'db': 'admin'},
            {'role': 'userAdminAnyDatabase', 'db': 'admin'}])

        collection = client.motor_test.test
        with test.assert_raises(OperationFailure):
            yield collection.count()

        yield client.admin.authenticate(
            MONGODB_X509_USERNAME, mechanism='MONGODB-X509')

        yield collection.remove()
        uri = ('mongodb://%s@%s:%d/?authMechanism='
               'MONGODB-X509' % (
               quote_plus(MONGODB_X509_USERNAME), host, port))

        # SSL options aren't supported in the URI....
        auth_uri_client = motor.MotorClient(
            uri, ssl_certfile=CLIENT_PEM, io_loop=self.io_loop)

        yield auth_uri_client.db.collection.find_one()

        # Cleanup.
        yield remove_all_users(client['$external'])
        yield client['$external'].logout()
