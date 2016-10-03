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

"""Discover environment and server configuration, initialize PyMongo client."""

import os
import socket

from test.utils import safe_get

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None

HAVE_TORNADO = True
TORNADO_VERSION = None
try:
    import tornado
    TORNADO_VERSION = tornado.version_info
except ImportError:
    HAVE_TORNADO = False
    tornado = None

HAVE_ASYNCIO = True
try:
    import asyncio
except ImportError:
    HAVE_ASYNCIO = False
    asyncio = None

import pymongo
import pymongo.errors
from pymongo.mongo_client import _partition_node

db_user = os.environ.get("DB_USER", "motor-test-root")
db_password = os.environ.get("DB_PASSWORD", "pass")

CERT_PATH = os.environ.get(
    'CERT_DIR',
    os.path.join(os.path.dirname(os.path.realpath(__file__)), 'certificates'))
CLIENT_PEM = os.path.join(CERT_PATH, 'client.pem')
CA_PEM = os.path.join(CERT_PATH, 'ca.pem')
MONGODB_X509_USERNAME = \
    "CN=client,OU=kerneluser,O=10Gen,L=New York City,ST=New York,C=US"


def is_server_resolvable():
    """Returns True if 'server' is resolvable."""
    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(1)
    try:
        socket.gethostbyname('server')
        return True
    except socket.error:
        return False
    finally:
        socket.setdefaulttimeout(socket_timeout)


class TestEnvironment(object):
    def __init__(self):
        self.initialized = False
        self.host = None
        self.port = None
        self.mongod_started_with_ssl = False
        self.mongod_validates_client_cert = False
        self.server_is_resolvable = is_server_resolvable()
        self.sync_cx = None
        self.is_mongos = False
        self.is_replica_set = False
        self.rs_name = None
        self.w = 1
        self.hosts = None
        self.arbiters = None
        self.primary = None
        self.secondaries = None
        self.v8 = False
        self.auth = False
        self.user_provided = False
        self.uri = None
        self.rs_uri = None

    def setup(self):
        assert not self.initialized
        self.setup_sync_cx()
        self.setup_auth()
        self.setup_mongos()
        self.setup_v8()
        self.initialized = True

    def teardown(self):
        if self.auth and not self.user_provided:
            # We created this user in setup_auth().
            self.sync_cx.admin.remove_user(db_user)

    def setup_sync_cx(self):
        """Get a synchronous PyMongo MongoClient and determine SSL config."""
        host = os.environ.get("DB_IP", "localhost")
        port = int(os.environ.get("DB_PORT", 27017))
        connectTimeoutMS = 100
        socketTimeoutMS = 30 * 1000
        try:
            client = pymongo.MongoClient(
                host, port,
                connectTimeoutMS=connectTimeoutMS,
                socketTimeoutMS=socketTimeoutMS,
                ssl=True)

            self.mongod_started_with_ssl = True
        except pymongo.errors.ConnectionFailure:
            try:
                client = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl_certfile=CLIENT_PEM)

                self.mongod_started_with_ssl = True
                self.mongod_validates_client_cert = True
            except pymongo.errors.ConnectionFailure:
                client = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl=False)

        response = client.admin.command('ismaster')
        if 'setName' in response:
            self.is_replica_set = True
            self.rs_name = str(response['setName'])
            self.w = len(response['hosts'])
            self.hosts = set([_partition_node(h) for h in response["hosts"]])
            host, port = self.primary = _partition_node(response['primary'])
            self.arbiters = set([
                _partition_node(h) for h in response.get("arbiters", [])])

            self.secondaries = [
                _partition_node(m) for m in response['hosts']
                if m != self.primary and m not in self.arbiters]

            # Reconnect to discovered primary.
            if self.mongod_started_with_ssl:
                client = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl_certfile=CLIENT_PEM)
            else:
                client = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl=False)

        self.sync_cx = client
        self.host = host
        self.port = port

    def setup_auth(self):
        """Set self.auth and self.uri, and maybe create an admin user."""
        try:
            cmd_line = self.sync_cx.admin.command('getCmdLineOpts')
        except pymongo.errors.OperationFailure as e:
            msg = e.details.get('errmsg', '')
            if e.code == 13 or 'unauthorized' in msg or 'login' in msg:
                # Unauthorized.
                self.auth = True
            else:
                raise
        else:
            # Either we're on mongod < 2.7.1 and we can connect over localhost
            # to check if --auth is in the command line. Or we're prohibited
            # from seeing the command line so we should try blindly to create
            # an admin user.
            try:
                authorization = safe_get(cmd_line,
                                         'parsed.security.authorization')
                if authorization:
                    self.auth = (authorization == 'enabled')
                else:
                    argv = cmd_line['argv']
                    self.auth = ('--auth' in argv or '--keyFile' in argv)
            except pymongo.errors.OperationFailure as e:
                if e.code == 13:
                    # Auth failure getting command line.
                    self.auth = True
                else:
                    raise

        if self.auth:
            uri_template = 'mongodb://%s:%s@%s:%s/admin'
            self.uri = uri_template % (db_user, db_password,
                                       self.host, self.port)

            # If the hostname 'server' is resolvable, this URI lets us use it
            # to test SSL hostname validation with auth.
            self.fake_hostname_uri = uri_template % (
                db_user, db_password, 'server', self.port)

            try:
                self.sync_cx.admin.add_user(db_user, db_password,
                                            roles=['root'])
            except pymongo.errors.OperationFailure:
                # User was added before setup(), e.g. by Mongo Orchestration.
                self.user_provided = True

            self.sync_cx.admin.authenticate(db_user, db_password)

        else:
            self.uri = 'mongodb://%s:%s/admin' % (
                self.host, self.port)

            self.fake_hostname_uri = 'mongodb://%s:%s/admin' % (
                'server', self.port)

        if self.rs_name:
            self.rs_uri = self.uri + '?replicaSet=' + self.rs_name

    def setup_mongos(self):
        """Set self.is_mongos."""
        response = self.sync_cx.admin.command('ismaster')
        self.is_mongos = response.get('msg') == 'isdbgrid'

    def setup_v8(self):
        """Determine if server is running SpiderMonkey or V8."""
        if self.sync_cx.server_info().get('javascriptEngine') == 'V8':
            self.v8 = True


env = TestEnvironment()
