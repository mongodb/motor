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

"""Generic tests for AsyncIOMotorClient and AsyncIOMotorReplicaSetClient."""

import asyncio
import time

import pymongo.errors
import pymongo.mongo_replica_set_client

from test.asyncio_tests import (asyncio_test,
                                remove_all_users,
                                server_is_master_with_slave,
                                skip_if_mongos)


class AsyncIOClientTestMixin(object):
    def get_client(self):
        raise NotImplementedError()

    def test_requests(self):
        for method in 'start_request', 'in_request', 'end_request':
            self.assertRaises(TypeError, getattr(self.get_client(), method))

    @asyncio_test
    def test_copy_db_argument_checking(self):
        cx = self.get_client()
        with self.assertRaises(TypeError):
            yield from cx.copy_database(4, 'foo')

        with self.assertRaises(TypeError):
            yield from cx.copy_database('foo', 4)

        with self.assertRaises(pymongo.errors.InvalidName):
            yield from cx.copy_database('foo', '$foo')

    @asyncio.coroutine
    def drop_databases(self, database_names, authenticated_client=None):
        cx = authenticated_client or self.get_client()
        for test_db_name in database_names:
            yield from cx.drop_database(test_db_name)

        # Due to SERVER-2329, databases may not disappear from a master
        # in a master-slave pair.
        if not (yield from server_is_master_with_slave(cx)):
            start = time.time()

            # There may be a race condition in the server's dropDatabase. Wait
            # for it to update its namespaces.
            db_names = yield from cx.database_names()
            while time.time() - start < 30:
                remaining_test_dbs = (
                    set(database_names).intersection(db_names))

                if not remaining_test_dbs:
                    # All test DBs are removed.
                    break

                yield from asyncio.sleep(0.1, loop=self.loop)
                db_names = yield from cx.database_names()

            for test_db_name in database_names:
                self.assertFalse(
                    test_db_name in db_names,
                    "%s not dropped" % test_db_name)

    @asyncio.coroutine
    def check_copydb_results(self, doc, test_db_names):
        cx = self.get_client()
        for test_db_name in test_db_names:
            self.assertEqual(
                doc,
                (yield from cx[test_db_name].test_collection.find_one()))

    @asyncio_test
    def test_copy_db(self):
        cx = self.get_client()
        target_db_name = 'motor_test_2'

        yield from cx.drop_database(target_db_name)
        yield from self.collection.remove()
        yield from self.collection.insert({'_id': 1})
        result = yield from cx.copy_database("motor_test", target_db_name)
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(
            {'_id': 1},
            (yield from cx[target_db_name].test_collection.find_one()))

        yield from cx.drop_database(target_db_name)

    @asyncio_test(timeout=300)
    def test_copy_db_concurrent(self):
        n_copies = 2
        target_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        cx = self.get_client()
        yield from cx.drop_database('motor_test')
        yield from self.drop_databases(target_db_names)

        # 2. Copy a test DB N times at once
        collection = cx.motor_test.test_collection
        yield from collection.insert({'_id': 1})
        futures = [
            cx.copy_database('motor_test', test_db_name)
            for test_db_name in target_db_names]

        results, _ = yield from asyncio.wait(futures, loop=self.loop)
        self.assertTrue(all(isinstance(i.result(), dict) for i in results))
        yield from self.check_copydb_results({'_id': 1}, target_db_names)
        yield from self.drop_databases(target_db_names)

    @asyncio_test
    def test_copy_db_auth(self):
        # SERVER-6427, can't copy database via mongos with auth.
        yield from skip_if_mongos(self.cx)

        yield from self.collection.remove()
        yield from self.collection.insert({'_id': 1})

        try:
            # self.cx is logged in as root.
            yield from self.cx.motor_test.add_user('mike', 'password')

            client = self.get_client()
            target_db_name = 'motor_test_2'

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield from client.copy_database(
                    'motor_test', target_db_name,
                    username='foo', password='bar')

            with self.assertRaises(pymongo.errors.OperationFailure):
                yield from client.copy_database(
                    'motor_test', target_db_name,
                    username='mike', password='bar')

            # Copy a database using name and password.
            yield from client.copy_database(
                'motor_test', target_db_name,
                username='mike', password='password')

            self.assertEqual(
                {'_id': 1},
                (yield from client[target_db_name].test_collection.find_one()))

            yield from client.drop_database(target_db_name)
        finally:
            yield from remove_all_users(self.cx.motor_test)

    @asyncio_test(timeout=30)
    def test_copy_db_auth_concurrent(self):
        # SERVER-6427, can't copy database via mongos with auth.
        yield from skip_if_mongos(self.cx)

        n_copies = 2
        test_db_names = ['motor_test_%s' % i for i in range(n_copies)]

        # 1. Drop old test DBs
        yield from self.cx.drop_database('motor_test')
        yield from self.collection.insert({'_id': 1})
        yield from self.drop_databases(test_db_names)

        # 2. Copy a test DB N times at once
        client = self.get_client()
        try:
            # self.cx is logged in as root.
            yield from self.cx.motor_test.add_user('mike', 'password')
            futures = [
                client.copy_database(
                    'motor_test', test_db_name,
                    username='mike', password='password')
                for test_db_name in test_db_names]

            results, _ = yield from asyncio.wait(futures, loop=self.loop)
            self.assertTrue(all(isinstance(i.result(), dict) for i in results))
            yield from self.check_copydb_results({'_id': 1}, test_db_names)
        finally:
            yield from remove_all_users(client.motor_test)
            yield from self.drop_databases(
                test_db_names,
                authenticated_client=self.cx)
