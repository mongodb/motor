# Copyright 2012 10gen, Inc.
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

"""Generic tests for MotorClient and MotorReplicaSetClient."""

import pymongo.errors
import pymongo.mongo_replica_set_client
from nose.plugins.skip import SkipTest
import time
from test import version
from test.utils import server_is_master_with_slave
from tornado import gen
from tornado.testing import gen_test

import motor
from test import assert_raises


class MotorClientTestMixin(object):
    def get_client(self):
        raise NotImplementedError()

    def test_requests(self):
        for method in 'start_request', 'in_request', 'end_request':
            self.assertRaises(TypeError, getattr(self.get_client(), method))

    @gen_test
    def test_copy_db_argument_checking(self):
        cx = self.get_client()
        with assert_raises(TypeError):
            yield cx.copy_database(4, 'foo')

        with assert_raises(TypeError):
            yield cx.copy_database('foo', 4)

        with assert_raises(pymongo.errors.InvalidName):
            yield cx.copy_database('foo', '$foo')

    @gen_test
    def test_copy_db_callback(self):
        cx = self.get_client()
        yield cx.drop_database('target')
        name = cx.motor_test.name
        (result, error), _ = yield gen.Task(
            cx.copy_database, name, 'target')

        self.assertTrue(isinstance(result, dict))
        self.assertEqual(error, None)

        yield cx.drop_database('target')

        client = motor.MotorClient('doesntexist')
        (result, error), _ = yield gen.Task(
            client.copy_database, name, 'target')

        self.assertEqual(result, None)
        self.assertTrue(isinstance(error, Exception))

    @gen.coroutine
    def drop_databases(self, database_names):
        cx = self.get_client()
        for test_db_name in database_names:
            yield cx.drop_database(test_db_name)

        # Due to SERVER-2329, databases may not disappear from a master
        # in a master-slave pair.
        if not (yield server_is_master_with_slave(cx)):
            start = time.time()

            # There may be a race condition in the server's dropDatabase. Wait
            # for it to update its namespaces.
            db_names = yield cx.database_names()
            while time.time() - start < 30:
                remaining_test_dbs = (
                    set(database_names).intersection(db_names))

                if not remaining_test_dbs:
                    # All test DBs are removed.
                    break

                yield self.pause(0.1)
                db_names = yield cx.database_names()

            for test_db_name in database_names:
                self.assertFalse(
                    test_db_name in db_names,
                    "%s not dropped" % test_db_name)

    @gen.coroutine
    def check_copydb_results(self, doc, test_db_names):
        cx = self.get_client()
        for test_db_name in test_db_names:
            self.assertEqual(
                doc,
                (yield cx[test_db_name].test_collection.find_one()))

    @gen_test
    def test_copy_db(self):
        cx = self.get_client()
        target_db_name = 'motor_test_2'

        yield cx.drop_database(target_db_name)
        yield self.collection.insert({'_id': 1})
        result = yield cx.copy_database("motor_test", target_db_name)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(
            {'_id': 1},
            (yield cx[target_db_name].test_collection.find_one()))

        yield cx.drop_database(target_db_name)

    @gen_test(timeout=300)
    def test_copy_db_concurrent(self):
        n_copies = 2
        target_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        cx = self.get_client()
        yield cx.drop_database('motor_test')
        yield self.drop_databases(target_db_names)

        # 2. Copy a test DB N times at once
        collection = cx.motor_test.test_collection
        yield collection.insert({'_id': 1})
        results = yield [
            cx.copy_database('motor_test', test_db_name)
            for test_db_name in target_db_names]

        self.assertTrue(all(isinstance(i, dict) for i in results))
        yield self.check_copydb_results({'_id': 1}, target_db_names)
        yield self.drop_databases(target_db_names)

    @gen_test
    def test_copy_db_auth(self):
        # See SERVER-6427.
        cx = self.get_client()
        if cx.is_mongos:
            raise SkipTest("Can't copy database with auth via mongos.")

        target_db_name = 'motor_test_2'

        collection = cx.motor_test.test_collection
        yield collection.remove()
        yield collection.insert({'_id': 1})

        yield cx.admin.add_user('admin', 'password')
        yield cx.admin.authenticate('admin', 'password')

        try:
            yield cx.motor_test.add_user('mike', 'password')

            with assert_raises(pymongo.errors.OperationFailure):
                yield cx.copy_database(
                    'motor_test', target_db_name,
                    username='foo', password='bar')

            with assert_raises(pymongo.errors.OperationFailure):
                yield cx.copy_database(
                    'motor_test', target_db_name,
                    username='mike', password='bar')

            # Copy a database using name and password.
            yield cx.copy_database(
                'motor_test', target_db_name,
                username='mike', password='password')

            self.assertEqual(
                {'_id': 1},
                (yield cx[target_db_name].test_collection.find_one()))

            yield cx.drop_database(target_db_name)
        finally:
            # Cleanup
            # TODO: refactor.
            if (yield version.at_least(cx, (2, 5, 4))):
                yield cx.motor_test.command({'dropAllUsersFromDatabase': 1})
            else:
                yield cx.motor_test.system.users.remove()

            yield cx.admin.remove_user('admin')

    @gen_test(timeout=30)
    def test_copy_db_auth_concurrent(self):
        cx = self.get_client()
        if cx.is_mongos:
            # See SERVER-6427.
            raise SkipTest("Can't copy database with auth via mongos.")

        n_copies = 2
        test_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        yield cx.drop_database('motor_test')
        yield self.drop_databases(test_db_names)

        # 2. Copy a test DB N times at once
        collection = cx.motor_test.test_collection
        yield collection.remove()
        yield collection.insert({'_id': 1})

        yield cx.admin.add_user('admin', 'password')
        yield cx.admin.authenticate('admin', 'password')

        try:
            yield cx.motor_test.add_user('mike', 'password')

            results = yield [
                cx.copy_database(
                    'motor_test', test_db_name,
                    username='mike', password='password')
                for test_db_name in test_db_names]

            self.assertTrue(all(isinstance(i, dict) for i in results))
            yield self.check_copydb_results({'_id': 1}, test_db_names)

        finally:
            # Cleanup
            # TODO: refactor.
            if (yield version.at_least(cx, (2, 5, 4))):
                yield cx.motor_test.command({'dropAllUsersFromDatabase': 1})
            else:
                yield cx.motor_test.system.users.remove()

            yield cx.admin.remove_user('admin')
            yield self.drop_databases(test_db_names)
