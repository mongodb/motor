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
import sys
import warnings
from functools import wraps

import pymongo.errors

from test import SkipTest
from test.utils import create_user
from test.version import Version

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None

HAVE_TORNADO = True
try:
    import tornado
except ImportError:
    HAVE_TORNADO = False
    tornado = None

HAVE_ASYNCIO = True
try:
    import asyncio
except ImportError:
    HAVE_ASYNCIO = False
    asyncio = None

HAVE_AIOHTTP = True
try:
    import aiohttp
except ImportError:
    HAVE_AIOHTTP = False
    aiohttp = None


# Copied from PyMongo.
def partition_node(node):
    """Split a host:port string into (host, int(port)) pair."""
    host = node
    port = 27017
    idx = node.rfind(':')
    if idx != -1:
        host, port = node[:idx], int(node[idx + 1:])
    if host.startswith('['):
        host = host[1:-1]
    return host, port


def connected(client):
    """Convenience, wait for a new PyMongo MongoClient to connect."""
    with warnings.catch_warnings():
        # Ignore warning that "ismaster" is always routed to primary even
        # if client's read preference isn't PRIMARY.
        warnings.simplefilter("ignore", UserWarning)
        client.admin.command('ismaster')  # Force connection.

    return client


# If these are set to the empty string, substitute None.
db_user = os.environ.get("DB_USER") or None
db_password = os.environ.get("DB_PASSWORD") or None

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
        self.is_standalone = False
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
        self.uri = None
        self.rs_uri = None
        self.version = None
        self.sessions_enabled = False
        self.fake_hostname_uri = None
        self.server_status = None

    def setup(self):
        assert not self.initialized
        self.setup_sync_cx()
        self.setup_auth_and_uri()
        self.setup_version()
        self.setup_v8()
        self.server_status = self.sync_cx.admin.command('serverStatus')
        self.initialized = True

    def setup_sync_cx(self):
        """Get a synchronous PyMongo MongoClient and determine SSL config."""
        host = os.environ.get("DB_IP", "localhost")
        port = int(os.environ.get("DB_PORT", 27017))
        connectTimeoutMS = 100
        serverSelectionTimeoutMS = 100
        socketTimeoutMS = 10000
        try:
            client = connected(pymongo.MongoClient(
                host, port,
                username=db_user,
                password=db_password,
                connectTimeoutMS=connectTimeoutMS,
                socketTimeoutMS=socketTimeoutMS,
                serverSelectionTimeoutMS=serverSelectionTimeoutMS,
                tlsCAFile=CA_PEM,
                ssl=True))

            self.mongod_started_with_ssl = True
        except pymongo.errors.ServerSelectionTimeoutError:
            try:
                client = connected(pymongo.MongoClient(
                    host, port,
                    username=db_user,
                    password=db_password,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    serverSelectionTimeoutMS=serverSelectionTimeoutMS,
                    tlsCAFile=CA_PEM,
                    tlsCertificateKeyFile=CLIENT_PEM))

                self.mongod_started_with_ssl = True
                self.mongod_validates_client_cert = True
            except pymongo.errors.ServerSelectionTimeoutError:
                client = connected(pymongo.MongoClient(
                    host, port,
                    username=db_user,
                    password=db_password,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    serverSelectionTimeoutMS=serverSelectionTimeoutMS))

        response = client.admin.command('ismaster')
        self.sessions_enabled = 'logicalSessionTimeoutMinutes' in response
        self.is_mongos = response.get('msg') == 'isdbgrid'
        if 'setName' in response:
            self.is_replica_set = True
            self.rs_name = str(response['setName'])
            self.w = len(response['hosts'])
            self.hosts = set([partition_node(h) for h in response["hosts"]])
            host, port = self.primary = partition_node(response['primary'])
            self.arbiters = set([
                partition_node(h) for h in response.get("arbiters", [])])

            self.secondaries = [
                partition_node(m) for m in response['hosts']
                if m != self.primary and m not in self.arbiters]
        elif not self.is_mongos:
            self.is_standalone = True

        # Reconnect to found primary, without short timeouts.
        if self.mongod_started_with_ssl:
            client = connected(pymongo.MongoClient(
                host, port,
                username=db_user,
                password=db_password,
                tlsCAFile=CA_PEM,
                tlsCertificateKeyFile=CLIENT_PEM))
        else:
            client = connected(pymongo.MongoClient(
                host, port,
                username=db_user,
                password=db_password,
                ssl=False))

        self.sync_cx = client
        self.host = host
        self.port = port

    def setup_auth_and_uri(self):
        """Set self.auth and self.uri."""
        if db_user or db_password:
            if not (db_user and db_password):
                sys.stderr.write(
                    "You must set both DB_USER and DB_PASSWORD, or neither\n")
                sys.exit(1)

            self.auth = True
            uri_template = 'mongodb://%s:%s@%s:%s/admin'
            self.uri = uri_template % (db_user, db_password,
                                       self.host, self.port)

            # If the hostname 'server' is resolvable, this URI lets us use it
            # to test SSL hostname validation with auth.
            self.fake_hostname_uri = uri_template % (
                db_user, db_password, 'server', self.port)

        else:
            self.uri = 'mongodb://%s:%s/admin' % (
                self.host, self.port)

            self.fake_hostname_uri = 'mongodb://%s:%s/admin' % (
                'server', self.port)

        if self.rs_name:
            self.rs_uri = self.uri + '?replicaSet=' + self.rs_name

    def setup_version(self):
        """Set self.version to the server's version."""
        self.version = Version.from_client(self.sync_cx)

    def setup_v8(self):
        """Determine if server is running SpiderMonkey or V8."""
        if self.sync_cx.server_info().get('javascriptEngine') == 'V8':
            self.v8 = True

    @property
    def storage_engine(self):
        try:
            return self.server_status.get("storageEngine", {}).get("name")
        except AttributeError:
            # Raised if self.server_status is None.
            return None

    def supports_transactions(self):
        if self.storage_engine == 'mmapv1':
            return False

        if self.version.at_least(4, 1, 8):
            return self.is_mongos or self.is_replica_set

        if self.version.at_least(4, 0):
            return self.is_replica_set

        return False

    def require(self, condition, msg, func=None):
        def make_wrapper(f):
            @wraps(f)
            def wrap(*args, **kwargs):
                if condition():
                    return f(*args, **kwargs)
                raise SkipTest(msg)

            return wrap

        if func is None:
            def decorate(f):
                return make_wrapper(f)

            return decorate
        return make_wrapper(func)

    def require_auth(self, func):
        """Run a test only if the server is started with auth."""
        return self.require(
            lambda: self.auth, "Server must be start with auth", func=func)

    def require_version_min(self, *ver):
        """Run a test only if the server version is at least ``version``."""
        other_version = Version(*ver)
        return self.require(lambda: self.version >= other_version,
                            "Server version must be at least %s"
                            % str(other_version))

    def require_version_max(self, *ver):
        """Run a test only if the server version is at most ``version``."""
        other_version = Version(*ver)
        return self.require(lambda: self.version <= other_version,
                            "Server version must be at most %s"
                            % str(other_version))

    def require_replica_set(self, func):
        """Run a test only if the client is connected to a replica set."""
        return self.require(lambda: self.is_replica_set,
                            "Not connected to a replica set",
                            func=func)

    def require_transactions(self, func):
        """Run a test only if the deployment might support transactions.

        *Might* because this does not test the FCV.
        """
        return self.require(self.supports_transactions,
                            "Transactions are not supported",
                            func=func)

    def create_user(self, dbname, user, pwd=None, roles=None, **kwargs):
        kwargs['writeConcern'] = {'w': self.w}
        return create_user(self.sync_cx[dbname], user, pwd, roles, **kwargs)

    def drop_user(self, dbname, user):
        self.sync_cx[dbname].command(
            'dropUser', user, writeConcern={'w': self.w})


env = TestEnvironment()
