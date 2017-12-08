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

from __future__ import unicode_literals

"""Utilities for testing Motor with Tornado."""

import concurrent.futures
from unittest import SkipTest

from mockupdb import MockupDB
from tornado import gen, testing

import motor
from test.test_environment import env, CA_PEM, CLIENT_PEM


@gen.coroutine
def get_command_line(client):
    command_line = yield client.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    raise gen.Return(command_line)


@gen.coroutine
def server_is_mongos(client):
    ismaster_response = yield client.admin.command('ismaster')
    raise gen.Return(ismaster_response.get('msg') == 'isdbgrid')


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    yield db.command({"dropAllUsersFromDatabase": 1})


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    yield db.command({"dropAllUsersFromDatabase": 1})


class MotorTest(testing.AsyncTestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super(MotorTest, self).setUp()

        if self.ssl and not env.mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        self.cx = self.motor_client()
        self.db = self.cx.motor_test
        self.collection = self.db.test_collection

    @gen.coroutine
    def make_test_data(self):
        yield self.collection.delete_many({})
        yield self.collection.insert_many([{'_id': i} for i in range(200)])

    make_test_data.__test__ = False

    def get_client_kwargs(self, **kwargs):
        if env.mongod_started_with_ssl:
            kwargs.setdefault('ssl_certfile', CLIENT_PEM)
            kwargs.setdefault('ssl_ca_certs', CA_PEM)

        kwargs.setdefault('ssl', env.mongod_started_with_ssl)
        kwargs.setdefault('io_loop', self.io_loop)

        return kwargs

    def motor_client(self, uri=None, *args, **kwargs):
        """Get a MotorClient.

        Ignores self.ssl, you must pass 'ssl' argument. You'll probably need to
        close the client to avoid file-descriptor problems after AsyncTestCase
        calls self.io_loop.close(all_fds=True).
        """
        return motor.MotorClient(
            uri or env.uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    def motor_rsc(self, uri=None, *args, **kwargs):
        """Get an open MotorClient for replica set.

        Ignores self.ssl, you must pass 'ssl' argument.
        """
        return motor.MotorClient(
            uri or env.rs_uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    def tearDown(self):
        env.sync_cx.motor_test.test_collection.delete_many({})
        self.cx.close()
        super(MotorTest, self).tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
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
        client = motor.motor_tornado.MotorClient(server.uri,
                                                 io_loop=self.io_loop)

        self.addCleanup(client.close)
        return client, server

    def run_thread(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)
