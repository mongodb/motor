# -*- coding: utf-8 -*-
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

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
from functools import partial
from bson import ObjectId

from gridfs.errors import FileExists, NoFile
from pymongo import MongoClient
from pymongo.errors import AutoReconnect, ConfigurationError
from pymongo.read_preferences import ReadPreference
from tornado import gen
from tornado.testing import gen_test

import motor
import test
from motor.motor_py3_compat import StringIO
from test import host, port, MotorTest, MotorReplicaSetTestBase, assert_raises


class MotorGridfsTest(MotorTest):
    @gen.coroutine
    def _reset(self):
        yield self.db.drop_collection("fs.files")
        yield self.db.drop_collection("fs.chunks")
        yield self.db.drop_collection("alt.files")
        yield self.db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridfsTest, self).setUp()
        self.fs = motor.MotorGridFS(self.db)

    def tearDown(self):
        self.io_loop.run_sync(self._reset)
        super(MotorGridfsTest, self).tearDown()

    @gen_test
    def test_gridfs(self):
        self.assertRaises(TypeError, motor.MotorGridFS, "foo")
        self.assertRaises(TypeError, motor.MotorGridFS, 5)

    @gen_test
    def test_get_version(self):
        # new_file creates a MotorGridIn.
        gin = yield self.fs.new_file(_id=1, filename='foo', field=0)
        yield gin.write(b'a')
        yield gin.close()

        yield self.fs.put(b'', filename='foo', field=1)
        yield self.fs.put(b'', filename='foo', field=2)

        gout = yield self.fs.get_version('foo')
        self.assertEqual(2, gout.field)
        gout = yield self.fs.get_version('foo', -3)
        self.assertEqual(0, gout.field)

        gout = yield self.fs.get_last_version('foo')
        self.assertEqual(2, gout.field)

    @gen_test
    def test_gridfs_callback(self):
        yield self.check_optional_callback(self.fs.new_file)
        yield self.check_optional_callback(partial(self.fs.put, b'a'))

        yield self.fs.put(b'foo', _id=1, filename='f')
        yield self.check_optional_callback(self.fs.get, 1)
        yield self.check_optional_callback(self.fs.get_version, 'f')
        yield self.check_optional_callback(self.fs.get_last_version, 'f')
        yield self.check_optional_callback(partial(self.fs.delete, 1))
        yield self.check_optional_callback(self.fs.list)
        yield self.check_optional_callback(self.fs.exists)

    @gen_test
    def test_basic(self):
        oid = yield self.fs.put(b"hello world")
        out = yield self.fs.get(oid)
        self.assertEqual(b"hello world", (yield out.read()))
        self.assertEqual(1, (yield self.db.fs.files.count()))
        self.assertEqual(1, (yield self.db.fs.chunks.count()))

        yield self.fs.delete(oid)
        with assert_raises(NoFile):
            yield self.fs.get(oid)

        self.assertEqual(0, (yield self.db.fs.files.count()))
        self.assertEqual(0, (yield self.db.fs.chunks.count()))

        with assert_raises(NoFile):
            yield self.fs.get("foo")
        
        self.assertEqual(
            "foo", (yield self.fs.put(b"hello world", _id="foo")))
        
        gridout = yield self.fs.get("foo")
        self.assertEqual(b"hello world", (yield gridout.read()))

    @gen_test
    def test_list(self):
        self.assertEqual([], (yield self.fs.list()))
        yield self.fs.put(b"hello world")
        self.assertEqual([], (yield self.fs.list()))

        yield self.fs.put(b"", filename="mike")
        yield self.fs.put(b"foo", filename="test")
        yield self.fs.put(b"", filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield self.fs.list())))

    @gen_test
    def test_alt_collection(self):
        db = self.db
        alt = motor.MotorGridFS(db, 'alt')
        oid = yield alt.put(b"hello world")
        gridout = yield alt.get(oid)
        self.assertEqual(b"hello world", (yield gridout.read()))
        self.assertEqual(1, (yield self.db.alt.files.count()))
        self.assertEqual(1, (yield self.db.alt.chunks.count()))

        yield alt.delete(oid)
        with assert_raises(NoFile):
            yield alt.get(oid)

        self.assertEqual(0, (yield self.db.alt.files.count()))
        self.assertEqual(0, (yield self.db.alt.chunks.count()))

        with assert_raises(NoFile):
            yield alt.get("foo")
        oid = yield alt.put(b"hello world", _id="foo")
        self.assertEqual("foo", oid)
        gridout = yield alt.get("foo")
        self.assertEqual(b"hello world", (yield gridout.read()))

        yield alt.put(b"", filename="mike")
        yield alt.put(b"foo", filename="test")
        yield alt.put(b"", filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield alt.list())))

    @gen_test
    def test_put_filelike(self):
        oid = yield self.fs.put(StringIO(b"hello world"), chunk_size=1)
        self.assertEqual(11, (yield self.cx.motor_test.fs.chunks.count()))
        gridout = yield self.fs.get(oid)
        self.assertEqual(b"hello world", (yield gridout.read()))

    @gen_test
    def test_put_callback(self):
        (oid, error), _ = yield gen.Task(self.fs.put, b"hello")
        self.assertTrue(isinstance(oid, ObjectId))
        self.assertEqual(None, error)

        (result, error), _ = yield gen.Task(self.fs.put, b"hello", _id=oid)
        self.assertEqual(None, result)
        self.assertTrue(isinstance(error, FileExists))

    @gen_test
    def test_put_duplicate(self):
        oid = yield self.fs.put(b"hello")
        with assert_raises(FileExists):
            yield self.fs.put(b"world", _id=oid)

    @gen_test
    def test_put_kwargs(self):
        # 'w' is not special here.
        oid = yield self.fs.put(b"hello", foo='bar', w=0)
        gridout = yield self.fs.get(oid)
        self.assertEqual('bar', gridout.foo)
        self.assertEqual(0, gridout.w)

    @gen_test
    def test_put_unacknowledged(self):
        client = self.motor_client(w=0)
        fs = motor.MotorGridFS(client.motor_test)
        with assert_raises(ConfigurationError):
            yield fs.put(b"hello")

        client.close()

    @gen_test
    def test_gridfs_find(self):
        yield self.fs.put(b"test2", filename="two")
        yield self.fs.put(b"test2+", filename="two")
        yield self.fs.put(b"test1", filename="one")
        yield self.fs.put(b"test2++", filename="two")
        cursor = self.fs.find().sort("_id", -1).skip(1).limit(2)
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertTrue(isinstance(grid_out, motor.MotorGridOut))
        self.assertEqual(b"test1", (yield grid_out.read()))

        cursor.rewind()
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertEqual(b"test1", (yield grid_out.read()))
        self.assertTrue((yield cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertEqual(b"test2+", (yield grid_out.read()))
        self.assertFalse((yield cursor.fetch_next))
        self.assertEqual(None, cursor.next_object())

        self.assertRaises(TypeError, self.fs.find, {}, {"_id": True})


class TestGridfsReplicaSet(MotorReplicaSetTestBase):
    @gen_test(timeout=10)
    def test_gridfs_replica_set(self):
        rsc = self.motor_rsc(
            w=test.env.w, wtimeout=5000,
            read_preference=ReadPreference.SECONDARY)

        fs = motor.MotorGridFS(rsc.motor_test)
        oid = yield fs.put(b'foo')
        gridout = yield fs.get(oid)
        content = yield gridout.read()
        self.assertEqual(b'foo', content)

    @gen_test
    def test_gridfs_secondary(self):
        primary_host, primary_port = test.env.primary
        primary = self.motor_client(primary_host, primary_port)
        if test.env.auth:
            yield primary.admin.authenticate(test.db_user, test.db_password)

        secondary_host, secondary_port = test.env.secondaries[0]

        secondary = self.motor_client(
            secondary_host, secondary_port,
            read_preference=ReadPreference.SECONDARY)

        if test.env.auth:
            yield secondary.admin.authenticate(test.db_user, test.db_password)

        yield primary.motor_test.drop_collection("fs.files")
        yield primary.motor_test.drop_collection("fs.chunks")

        # Should detect it's connected to secondary and not attempt to
        # create index
        fs = motor.MotorGridFS(secondary.motor_test)

        # This won't detect secondary, raises error
        with assert_raises(AutoReconnect):
            yield fs.put(b'foo')

    def tearDown(self):
        test.env.sync_cx.motor_test.drop_collection('fs.files')
        test.env.sync_cx.motor_test.drop_collection('fs.chunks')
        super(TestGridfsReplicaSet, self).tearDown()


if __name__ == "__main__":
    unittest.main()
