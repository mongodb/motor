# Copyright 2017-present MongoDB, Inc.
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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import copy
import sys
import unittest
from test import SkipTest
from test.test_environment import env
from test.tornado_tests import MotorTest
from test.utils import TestListener, session_ids

from pymongo import IndexModel, InsertOne
from pymongo.errors import InvalidOperation
from tornado.testing import gen_test


class MotorSessionTest(MotorTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not env.sessions_enabled:
            raise SkipTest("Sessions not supported")

    async def _test_ops(self, client, *ops):
        listener = client.options.event_listeners[0]

        for f, args, kw in ops:
            # Simulate "async with" on all Pythons.
            s = await client.start_session()
            try:
                listener.results.clear()
                # In case "f" modifies its inputs.
                args2 = copy.copy(args)
                kw2 = copy.copy(kw)
                kw2["session"] = s
                await f(*args2, **kw2)
                for event in listener.results["started"]:
                    self.assertTrue(
                        "lsid" in event.command,
                        "%s sent no lsid with %s" % (f.__name__, event.command_name),
                    )

                    self.assertEqual(
                        s.session_id,
                        event.command["lsid"],
                        "%s sent wrong lsid with %s" % (f.__name__, event.command_name),
                    )

                self.assertFalse(s.has_ended)
            finally:
                await s.end_session()

            with self.assertRaises(InvalidOperation) as ctx:
                await f(*args2, **kw2)

            self.assertIn("ended session", str(ctx.exception))

        # No explicit session.
        for f, args, kw in ops:
            listener.results.clear()
            await f(*args, **kw)
            self.assertGreaterEqual(len(listener.results["started"]), 1)
            lsids = []
            for event in listener.results["started"]:
                self.assertTrue(
                    "lsid" in event.command,
                    "%s sent no lsid with %s" % (f.__name__, event.command_name),
                )

                lsids.append(event.command["lsid"])

            if "PyPy" not in sys.version:
                # Server session was returned to pool. Ignore interpreters with
                # non-deterministic GC.
                for lsid in lsids:
                    self.assertIn(
                        lsid,
                        session_ids(client),
                        "%s did not return implicit session to pool" % (f.__name__,),
                    )

    @gen_test
    async def test_database(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])

        db = client.pymongo_test
        ops = [
            (db.command, ["ping"], {}),
            (db.drop_collection, ["collection"], {}),
            (db.create_collection, ["collection"], {}),
            (db.list_collection_names, [], {}),
        ]

        await self._test_ops(client, *ops)

    @gen_test(timeout=30)
    async def test_collection(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])
        await client.drop_database("motor_test")

        coll = client.motor_test.test_collection

        async def list_indexes(session=None):
            await coll.list_indexes(session=session).to_list(length=None)

        async def aggregate(session=None):
            await coll.aggregate([], session=session).to_list(length=None)

        # Test some collection methods - the rest are in test_cursor.
        await self._test_ops(
            client,
            (coll.drop, [], {}),
            (coll.bulk_write, [[InsertOne({})]], {}),
            (coll.insert_one, [{}], {}),
            (coll.insert_many, [[{}, {}]], {}),
            (coll.replace_one, [{}, {}], {}),
            (coll.update_one, [{}, {"$set": {"a": 1}}], {}),
            (coll.update_many, [{}, {"$set": {"a": 1}}], {}),
            (coll.delete_one, [{}], {}),
            (coll.delete_many, [{}], {}),
            (coll.find_one_and_replace, [{}, {}], {}),
            (coll.find_one_and_update, [{}, {"$set": {"a": 1}}], {}),
            (coll.find_one_and_delete, [{}, {}], {}),
            (coll.rename, ["collection2"], {}),
            # Drop collection2 between tests of "rename", above.
            (client.motor_test.drop_collection, ["collection2"], {}),
            (coll.distinct, ["a"], {}),
            (coll.find_one, [], {}),
            (coll.count_documents, [{}], {}),
            (coll.create_indexes, [[IndexModel("a")]], {}),
            (coll.create_index, ["a"], {}),
            (coll.drop_index, ["a_1"], {}),
            (coll.drop_indexes, [], {}),
            (list_indexes, [], {}),
            (coll.index_information, [], {}),
            (coll.options, [], {}),
            (aggregate, [], {}),
        )

    @gen_test
    async def test_cursor(self):
        listener = TestListener()
        client = self.motor_client(event_listeners=[listener])
        await self.make_test_data()

        coll = client.motor_test.test_collection

        s = await client.start_session()
        # Simulate "async with" on all Pythons.
        try:
            listener.results.clear()
            cursor = coll.find(session=s)
            await cursor.to_list(length=None)
            self.assertEqual(len(listener.results["started"]), 2)
            for event in listener.results["started"]:
                self.assertTrue(
                    "lsid" in event.command, "find sent no lsid with %s" % (event.command_name,)
                )

                self.assertEqual(
                    s.session_id,
                    event.command["lsid"],
                    "find sent wrong lsid with %s" % (event.command_name,),
                )
        finally:
            await s.end_session()

        with self.assertRaises(InvalidOperation) as ctx:
            await coll.find(session=s).to_list(length=None)

        self.assertIn("ended session", str(ctx.exception))

        # No explicit session.
        listener.results.clear()
        cursor = coll.find()
        await cursor.to_list(length=None)
        self.assertEqual(len(listener.results["started"]), 2)
        event0 = listener.first_command_started()
        self.assertTrue(
            "lsid" in event0.command, "find sent no lsid with %s" % (event0.command_name,)
        )

        lsid = event0.command["lsid"]

        for event in listener.results["started"][1:]:
            self.assertTrue(
                "lsid" in event.command, "find sent no lsid with %s" % (event.command_name,)
            )

            self.assertEqual(
                lsid, event.command["lsid"], "find sent wrong lsid with %s" % (event.command_name,)
            )

    @gen_test
    async def test_options(self):
        s = await self.cx.start_session()
        self.assertTrue(s.options.causal_consistency)
        s = await self.cx.start_session(False)
        self.assertFalse(s.options.causal_consistency)
        s = await self.cx.start_session(causal_consistency=True)
        self.assertTrue(s.options.causal_consistency)
        s = await self.cx.start_session(causal_consistency=False)
        self.assertFalse(s.options.causal_consistency)


if __name__ == "__main__":
    unittest.main()
