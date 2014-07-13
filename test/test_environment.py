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

"""Discover environment and server configuration, initialize PyMongo client."""

import os

HAVE_SSL = True
try:
    import ssl
except ImportError:
    HAVE_SSL = False
    ssl = None

import pymongo
import pymongo.errors
from pymongo.mongo_client import _partition_node

host = os.environ.get("DB_IP", "localhost")
port = int(os.environ.get("DB_PORT", 27017))
db_user = 'motor-test-root'
db_password = 'pass'

CERT_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'certificates')
CLIENT_PEM = os.path.join(CERT_PATH, 'client.pem')
CA_PEM = os.path.join(CERT_PATH, 'ca.pem')


class TestEnvironment(object):
    def __init__(self):
        self.initialized = False
        self.mongod_started_with_ssl = False
        self.mongod_validates_client_cert = False
        self.sync_cx = None
        self.is_replica_set = False
        self.rs_name = None
        self.w = None
        self.hosts = None
        self.arbiters = None
        self.primary = None
        self.secondaries = None
        self.v8 = False
        self.auth = False
        self.uri = None
        self.rs_uri = None

    def setup(self):
        """Called once from setup_package."""
        assert not self.initialized
        self.setup_sync_cx()
        self.setup_auth()
        self.setup_rs()
        self.setup_v8()
        self.initialized = True

    def setup_sync_cx(self):
        """Get a synchronous PyMongo MongoClient and determine SSL config."""
        connectTimeoutMS = socketTimeoutMS = 30 * 1000
        try:
            self.sync_cx = pymongo.MongoClient(
                host, port,
                connectTimeoutMS=connectTimeoutMS,
                socketTimeoutMS=socketTimeoutMS,
                ssl=True)

            self.mongod_started_with_ssl = True
        except pymongo.errors.ConnectionFailure:
            try:
                self.sync_cx = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl_certfile=CLIENT_PEM)

                self.mongod_started_with_ssl = True
                self.mongod_validates_client_cert = True
            except pymongo.errors.ConnectionFailure:
                self.sync_cx = pymongo.MongoClient(
                    host, port,
                    connectTimeoutMS=connectTimeoutMS,
                    socketTimeoutMS=socketTimeoutMS,
                    ssl=False)

    def setup_auth(self):
        """Set self.auth and self.uri, and maybe create an admin user."""
        # Either we're on mongod < 2.7.1 and we can connect over localhost to
        # check if --auth is in the command line. Or we're prohibited from
        # seeing the command line so we should try blindly to create an admin
        # user.
        try:
            argv = self.sync_cx.admin.command('getCmdLineOpts')['argv']
            self.auth = ('--auth' in argv or '--keyFile' in argv)
        except pymongo.errors.OperationFailure as e:
            if e.code == 13:
                # Auth failure getting command line.
                self.auth = True
            else:
                raise

        if self.auth:
            self.uri = 'mongodb://%s:%s@%s:%s/admin' % (
                db_user, db_password, host, port)

            # TODO: use PyMongo's add_user once that's fixed.
            self.sync_cx.admin.command(
                'createUser', db_user, pwd=db_password, roles=['root'])

            self.sync_cx.admin.authenticate(db_user, db_password)

        else:
            self.uri = 'mongodb://%s:%s/admin' % (host, port)

    def setup_rs(self):
        """Determine server's replica set config."""
        response = self.sync_cx.admin.command('ismaster')
        if 'setName' in response:
            self.is_replica_set = True
            self.rs_name = str(response['setName'])
            self.rs_uri = self.uri + '?replicaSet=' + self.rs_name
            self.w = len(response['hosts'])
            self.hosts = set([_partition_node(h) for h in response["hosts"]])
            self.arbiters = set([
                _partition_node(h) for h in response.get("arbiters", [])])

            repl_set_status = self.sync_cx.admin.command('replSetGetStatus')
            primary_info = [
                m for m in repl_set_status['members']
                if m['stateStr'] == 'PRIMARY'][0]

            self.primary = _partition_node(primary_info['name'])
            self.secondaries = [
                _partition_node(m['name']) for m in repl_set_status['members']
                if m['stateStr'] == 'SECONDARY']

    def setup_v8(self):
        """Determine if server is running SpiderMonkey or V8."""
        if self.sync_cx.server_info().get('javascriptEngine') == 'V8':
            self.v8 = True


env = TestEnvironment()
