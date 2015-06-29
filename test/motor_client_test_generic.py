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

"""Generic tests for MotorClient and MotorReplicaSetClient."""
import time

import pymongo.errors
import pymongo.mongo_replica_set_client
from tornado import gen
from tornado.testing import gen_test

import motor
from test import assert_raises, env, SkipTest
from test.utils import server_is_master_with_slave, remove_all_users
from test.utils import skip_if_mongos


class MotorClientTestMixin(object):
    def get_client(self, *args, **kwargs):
        raise NotImplementedError()

    def test_requests(self):
        for method in 'start_request', 'in_request', 'end_request':
            self.assertRaises(TypeError, getattr(self.get_client(), method))

    # no more copy_database method
    # @gen_test
    # def test_copy_db_argument_checking(self):
    #     cx = self.get_client()
    #     with assert_raises(TypeError):
    #         yield cx.copy_database(4, 'foo')
    #
    #     with assert_raises(TypeError):
    #         yield cx.copy_database('foo', 4)
    #
    #     with assert_raises(pymongo.errors.InvalidName):
    #         yield cx.copy_database('foo', '$foo')
    #
    # @gen_test
    # def test_copy_db_callback(self):
    #     cx = self.get_client()
    #     yield cx.drop_database('target')
    #     name = cx.motor_test.name
    #     (result, error), _ = yield gen.Task(
    #         cx.copy_database, name, 'target')
    #
    #     self.assertTrue(isinstance(result, dict))
    #     self.assertEqual(error, None)
    #
    #     yield cx.drop_database('target')
    #
    #     client = motor.MotorClient('doesntexist', connectTimeoutMS=10)
    #     (result, error), _ = yield gen.Task(
    #         client.copy_database, name, 'target')
    #
    #     self.assertEqual(result, None)
    #     self.assertTrue(isinstance(error, Exception))

    @gen.coroutine
    def drop_databases(self, database_names, authenticated_client=None):
        cx = authenticated_client or self.get_client()
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

    # no more copy_database method
    # @gen_test
    # def test_copy_db(self):
    #     # This will catch any socket leaks.
    #     cx = self.get_client(max_pool_size=1, waitQueueTimeoutMS=1)
    #     target_db_name = 'motor_test_2'
    #
    #     yield cx.drop_database(target_db_name)
    #     yield self.collection.insert({'_id': 1})
    #     result = yield cx.copy_database("motor_test", target_db_name)
    #     self.assertTrue(isinstance(result, dict))
    #     self.assertEqual(
    #         {'_id': 1},
    #         (yield cx[target_db_name].test_collection.find_one()))
    #
    #     yield cx.drop_database(target_db_name)
    #
    # @gen_test(timeout=300)
    # def test_copy_db_concurrent(self):
    #     n_copies = 2
    #     target_db_names = ['motor_test_%s' % i for i in range(n_copies)]
    #
    #     # 1. Drop old test DBs
    #     cx = self.get_client()
    #     yield cx.drop_database('motor_test')
    #     yield self.drop_databases(target_db_names)
    #
    #     # 2. Copy a test DB N times at once
    #     collection = cx.motor_test.test_collection
    #     yield collection.insert({'_id': 1})
    #     results = yield [
    #         cx.copy_database('motor_test', test_db_name)
    #         for test_db_name in target_db_names]
    #
    #     self.assertTrue(all(isinstance(i, dict) for i in results))
    #     yield self.check_copydb_results({'_id': 1}, target_db_names)
    #     yield self.drop_databases(target_db_names)
    #
    # @gen_test
    # def test_copy_db_auth(self):
    #     if env.mongod_started_with_ssl:
    #         raise SkipTest("Can't copy DB with auth over SSL, SERVER-14700")
    #
    #     # SERVER-6427, can't copy database via mongos with auth.
    #     yield skip_if_mongos(self.cx)
    #
    #     yield self.collection.remove()
    #     yield self.collection.insert({'_id': 1})
    #
    #     try:
    #         # self.cx is logged in as root.
    #         yield self.cx.motor_test.add_user('mike', 'password')
    #
    #         # This will catch any socket leaks.
    #         client = self.get_client(max_pool_size=1, waitQueueTimeoutMS=1)
    #         target_db_name = 'motor_test_2'
    #
    #         with assert_raises(pymongo.errors.OperationFailure):
    #             yield client.copy_database(
    #                 'motor_test', target_db_name,
    #                 username='foo', password='bar')
    #
    #         with assert_raises(pymongo.errors.OperationFailure):
    #             yield client.copy_database(
    #                 'motor_test', target_db_name,
    #                 username='mike', password='bar')
    #
    #         # Copy a database using name and password.
    #         yield client.copy_database(
    #             'motor_test', target_db_name,
    #             username='mike', password='password')
    #
    #         self.assertEqual(
    #             {'_id': 1},
    #             (yield client[target_db_name].test_collection.find_one()))
    #
    #         yield client.drop_database(target_db_name)
    #     finally:
    #         yield remove_all_users(self.cx.motor_test)
    #
    # @gen_test(timeout=30)
    # def test_copy_db_auth_concurrent(self):
    #     if env.mongod_started_with_ssl:
    #         raise SkipTest("Can't copy DB with auth over SSL, SERVER-14700")
    #
    #     # SERVER-6427, can't copy database via mongos with auth.
    #     yield skip_if_mongos(self.cx)
    #
    #     n_copies = 2
    #     test_db_names = ['motor_test_%s' % i for i in range(n_copies)]
    #
    #     # 1. Drop old test DBs
    #     yield self.cx.drop_database('motor_test')
    #     yield self.collection.insert({'_id': 1})
    #     yield self.drop_databases(test_db_names)
    #
    #     # 2. Copy a test DB N times at once
    #     try:
    #         # self.cx is logged in as root.
    #         yield self.cx.motor_test.add_user('mike', 'password')
    #
    #         client = self.get_client()
    #         results = yield [
    #             client.copy_database(
    #                 'motor_test', test_db_name,
    #                 username='mike', password='password')
    #             for test_db_name in test_db_names]
    #
    #         self.assertTrue(all(isinstance(i, dict) for i in results))
    #         yield self.check_copydb_results({'_id': 1}, test_db_names)
    #
    #     finally:
    #         yield remove_all_users(client.motor_test)
    #         yield self.drop_databases(
    #             test_db_names,
    #             authenticated_client=self.cx)
