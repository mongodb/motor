# Copyright 2018-present MongoDB, Inc.
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

from test.utils import TestListener

from pymongo.read_concern import ReadConcern

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
from test.test_environment import env
from test.tornado_tests import MotorTest

from pymongo import ReadPreference, WriteConcern
from pymongo.errors import ConnectionFailure, OperationFailure
from tornado.testing import gen_test

from motor import core


class PatchSessionTimeout(object):
    """Patches the client_session's with_transaction timeout for testing."""

    def __init__(self, mock_timeout):
        self.real_timeout = core._WITH_TRANSACTION_RETRY_TIME_LIMIT
        self.mock_timeout = mock_timeout

    def __enter__(self):
        core._WITH_TRANSACTION_RETRY_TIME_LIMIT = self.mock_timeout
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        core._WITH_TRANSACTION_RETRY_TIME_LIMIT = self.real_timeout


class TestTransactionsConvenientAPI(MotorTest):
    @env.require_transactions
    @gen_test
    async def test_basic(self):
        # Create the collection.
        await self.collection.insert_one({})

        async def coro(session):
            await self.collection.insert_one({"_id": 1}, session=session)

        async with await self.cx.start_session() as s:
            await s.with_transaction(
                coro,
                read_concern=ReadConcern("local"),
                write_concern=WriteConcern("majority"),
                read_preference=ReadPreference.PRIMARY,
                max_commit_time_ms=30000,
            )

        doc = await self.collection.find_one({"_id": 1})
        self.assertEqual(doc, {"_id": 1})

    @env.require_transactions
    @gen_test
    async def test_callback_raises_custom_error(self):
        class _MyException(Exception):
            pass

        async def coro_raise_error(_):
            raise _MyException()

        async with await self.cx.start_session() as s:
            with self.assertRaises(_MyException):
                await s.with_transaction(coro_raise_error)

    @env.require_transactions
    @gen_test
    async def test_callback_returns_value(self):
        async def callback(_):
            return "Foo"

        async with await self.cx.start_session() as s:
            self.assertEqual(await s.with_transaction(callback), "Foo")

        await self.db.test.insert_one({})

        async def callback(session):
            await self.db.test.insert_one({}, session=session)
            return "Foo"

        async with await self.cx.start_session() as s:
            self.assertEqual(await s.with_transaction(callback), "Foo")

    @env.require_transactions
    @gen_test
    async def test_callback_not_retried_after_timeout(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])
        coll = client[self.db.name].test

        async def callback(session):
            await coll.insert_one({}, session=session)
            err = {
                "ok": 0,
                "errmsg": "Transaction 7819 has been aborted.",
                "code": 251,
                "codeName": "NoSuchTransaction",
                "errorLabels": ["TransientTransactionError"],
            }
            raise OperationFailure(err["errmsg"], err["code"], err)

        # Create the collection.
        await coll.insert_one({})
        listener.results.clear()
        async with await client.start_session() as s:
            with PatchSessionTimeout(0):
                with self.assertRaises(OperationFailure):
                    await s.with_transaction(callback)

        self.assertEqual(listener.started_command_names(), ["insert", "abortTransaction"])

    @env.require_transactions
    @gen_test
    async def test_callback_not_retried_after_commit_timeout(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])
        coll = client[self.db.name].test

        async def callback(session):
            await coll.insert_one({}, session=session)

        # Create the collection.
        await coll.insert_one({})
        await self.set_fail_point(
            client,
            {
                "configureFailPoint": "failCommand",
                "mode": {"times": 1},
                "data": {
                    "failCommands": ["commitTransaction"],
                    "errorCode": 251,  # NoSuchTransaction
                },
            },
        )
        listener.results.clear()

        async with await client.start_session() as s:
            with PatchSessionTimeout(0):
                with self.assertRaises(OperationFailure):
                    await s.with_transaction(callback)

        self.assertEqual(listener.started_command_names(), ["insert", "commitTransaction"])

        await self.set_fail_point(client, {"configureFailPoint": "failCommand", "mode": "off"})

    @env.require_transactions
    @gen_test
    async def test_commit_not_retried_after_timeout(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])
        coll = client[self.db.name].test

        async def callback(session):
            await coll.insert_one({}, session=session)

        # Create the collection.
        await coll.insert_one({})
        await self.set_fail_point(
            client,
            {
                "configureFailPoint": "failCommand",
                "mode": {"times": 2},
                "data": {"failCommands": ["commitTransaction"], "closeConnection": True},
            },
        )
        listener.results.clear()

        async with await client.start_session() as s:
            with PatchSessionTimeout(0):
                with self.assertRaises(ConnectionFailure):
                    await s.with_transaction(callback)

        # One insert for the callback and two commits (includes the automatic
        # retry).
        self.assertEqual(
            listener.started_command_names(), ["insert", "commitTransaction", "commitTransaction"]
        )
        self.set_fail_point(client, {"configureFailPoint": "failCommand", "mode": "off"})


if __name__ == "__main__":
    unittest.main()
