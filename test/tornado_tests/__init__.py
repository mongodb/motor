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
import datetime
import functools

try:
    # Python 2.6.
    from unittest2 import SkipTest
    import unittest2 as unittest
except ImportError:
    from unittest import SkipTest  # If this fails you need unittest2.
    import unittest

from mockupdb import MockupDB
from tornado import gen, testing

import motor
from test.test_environment import env, CLIENT_PEM
from test.version import padded, _parse_version_string


@gen.coroutine
def version(client):
    info = yield client.server_info()
    raise gen.Return(_parse_version_string(info["version"]))


@gen.coroutine
def at_least(client, min_version):
    client_version = yield version(client)
    raise gen.Return(client_version >= tuple(padded(min_version, 4)))


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
    version_check = yield at_least(db.client, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    version_check = yield at_least(db.client, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})


class PauseMixin(object):
    @gen.coroutine
    def pause(self, seconds):
        yield gen.Task(
            self.io_loop.add_timeout, datetime.timedelta(seconds=seconds))


class MotorTest(PauseMixin, testing.AsyncTestCase):
    longMessage = True  # Used by unittest.TestCase
    ssl = False  # If True, connect with SSL, skip if mongod isn't SSL

    def setUp(self):
        super(MotorTest, self).setUp()

        if self.ssl and not env.mongod_started_with_ssl:
            raise SkipTest("mongod doesn't support SSL, or is down")

        if env.auth:
            self.cx = self.motor_client(env.uri, ssl=self.ssl)
        else:
            self.cx = self.motor_client(ssl=self.ssl)

        self.db = self.cx.motor_test
        self.collection = self.db.test_collection

    @gen.coroutine
    def make_test_data(self):
        yield self.collection.remove()
        yield self.collection.insert([{'_id': i} for i in range(200)])

    make_test_data.__test__ = False

    def get_client_kwargs(self, **kwargs):
        kwargs.setdefault('io_loop', self.io_loop)
        ssl = env.mongod_started_with_ssl
        kwargs.setdefault('ssl', ssl)
        if kwargs['ssl'] and env.mongod_validates_client_cert:
            kwargs.setdefault('ssl_certfile', CLIENT_PEM)

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
        """Get an open MotorReplicaSetClient. Ignores self.ssl, you must pass
        'ssl' argument. You'll probably need to close the client to avoid
        file-descriptor problems after AsyncTestCase calls
        self.io_loop.close(all_fds=True).
        """
        return motor.MotorReplicaSetClient(
            uri or env.rs_uri,
            *args,
            **self.get_client_kwargs(**kwargs))

    @gen.coroutine
    def check_optional_callback(self, fn, *args, **kwargs):
        """Take a function and verify that it accepts a 'callback' parameter
        and properly type-checks it. If 'required', check that fn requires
        a callback.

        NOTE: This method can call fn several times, so it should be relatively
        free of side-effects. Otherwise you should test fn without this method.

        :Parameters:
          - `fn`: A function that accepts a callback
          - `required`: Whether `fn` should require a callback or not
          - `callback`: To be called with ``(None, error)`` when done
        """
        partial_fn = functools.partial(fn, *args, **kwargs)
        self.assertRaises(TypeError, partial_fn, callback='foo')
        self.assertRaises(TypeError, partial_fn, callback=1)

        # Should not raise
        yield partial_fn(callback=None)

        # Should not raise
        (result, error), _ = yield gen.Task(partial_fn)
        if error:
            raise error

    def tearDown(self):
        env.sync_cx.motor_test.test_collection.remove()
        self.cx.close()
        super(MotorTest, self).tearDown()


class MotorReplicaSetTestBase(MotorTest):
    def setUp(self):
        super(MotorReplicaSetTestBase, self).setUp()
        if not env.is_replica_set:
            raise SkipTest("Not connected to a replica set")

        self.rsc = self.motor_rsc()
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

        return client, server

    def run_thread(self, fn, *args, **kwargs):
        return self.executor.submit(fn, *args, **kwargs)
