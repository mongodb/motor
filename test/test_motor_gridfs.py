# -*- coding: utf-8 -*-
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

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
from functools import partial

from bson.py3compat import b, StringIO
from gridfs.errors import FileExists, NoFile
from pymongo import MongoClient
from pymongo.errors import AutoReconnect
from pymongo.read_preferences import ReadPreference
from tornado.testing import gen_test

import motor
from test import host, port, MotorTest, MotorReplicaSetTestBase, assert_raises
from test import AssertEqual


class MotorGridfsTest(MotorTest):
    def _reset(self):
        self.sync_db.drop_collection("fs.files")
        self.sync_db.drop_collection("fs.chunks")
        self.sync_db.drop_collection("alt.files")
        self.sync_db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridfsTest, self).setUp()
        self._reset()

    def tearDown(self):
        self._reset()
        super(MotorGridfsTest, self).tearDown()

    @gen_test
    def test_gridfs(self):
        self.assertRaises(TypeError, motor.MotorGridFS, "foo")
        self.assertRaises(TypeError, motor.MotorGridFS, 5)
        db = self.cx.pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)

        # new_file should be an already-open MotorGridIn.
        gin = yield motor.Op(fs.new_file, _id=1, filename='foo')
        self.assertTrue(gin.delegate)
        yield motor.Op(gin.write, b('a'))  # No error
        yield motor.Op(gin.close)

        # get, get_version, and get_last_version should be already-open
        # MotorGridOut instances
        gout = yield motor.Op(fs.get, 1)
        self.assertTrue(gout.delegate)
        gout = yield motor.Op(fs.get_version, 'foo')
        self.assertTrue(gout.delegate)
        gout = yield motor.Op(fs.get_last_version, 'foo')
        self.assertTrue(gout.delegate)

    @gen_test
    def test_gridfs_callback(self):
        db = self.cx.pymongo_test
        fs = motor.MotorGridFS(db)
        yield self.check_optional_callback(fs.open)

        fs = yield motor.Op(motor.MotorGridFS(db).open)
        yield self.check_required_callback(fs.new_file)
        yield self.check_optional_callback(partial(fs.put, b('a')))

        yield motor.Op(fs.put, b('foo'), _id=1, filename='f')
        yield self.check_required_callback(fs.get, 1)
        yield self.check_required_callback(fs.get_version, 'f')
        yield self.check_required_callback(fs.get_last_version, 'f')
        yield self.check_optional_callback(partial(fs.delete, 1))
        yield self.check_required_callback(fs.list)
        yield self.check_required_callback(fs.exists)

    @gen_test
    def test_basic(self):
        db = self.cx.pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)
        oid = yield motor.Op(fs.put, b("hello world"))
        out = yield motor.Op(fs.get, oid)
        yield AssertEqual(b("hello world"), out.read)
        yield AssertEqual(1, db.fs.files.count)
        yield AssertEqual(1, db.fs.chunks.count)

        yield motor.Op(fs.delete, oid)
        with assert_raises(NoFile):
            yield motor.Op(fs.get, oid)
        yield AssertEqual(0, db.fs.files.count)
        yield AssertEqual(0, db.fs.chunks.count)

        with assert_raises(NoFile):
            yield motor.Op(fs.get, "foo")
        yield AssertEqual("foo", fs.put, b("hello world"), _id="foo")
        gridout = yield motor.Op(fs.get, "foo")
        yield AssertEqual(b("hello world"), gridout.read)

    @gen_test
    def test_list(self):
        db = self.cx.pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)
        self.assertEqual([], (yield motor.Op(fs.list)))
        yield motor.Op(fs.put, b("hello world"))
        self.assertEqual([], (yield motor.Op(fs.list)))

        yield motor.Op(fs.put, b(""), filename="mike")
        yield motor.Op(fs.put, b("foo"), filename="test")
        yield motor.Op(fs.put, b(""), filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield motor.Op(fs.list))))

    @gen_test
    def test_alt_collection(self):
        db = self.cx.pymongo_test
        alt = yield motor.Op(motor.MotorGridFS(db, 'alt').open)
        oid = yield motor.Op(alt.put, b("hello world"))
        gridout = yield motor.Op(alt.get, oid)
        self.assertEqual(b("hello world"), (yield motor.Op(gridout.read)))
        self.assertEqual(1, (yield motor.Op(db.alt.files.count)))
        self.assertEqual(1, (yield motor.Op(db.alt.chunks.count)))

        yield motor.Op(alt.delete, oid)
        with assert_raises(NoFile):
            yield motor.Op(alt.get, oid)
        self.assertEqual(0, (yield motor.Op(db.alt.files.count)))
        self.assertEqual(0, (yield motor.Op(db.alt.chunks.count)))

        with assert_raises(NoFile):
            yield motor.Op(alt.get, "foo")
        oid = yield motor.Op(alt.put, b("hello world"), _id="foo")
        self.assertEqual("foo", oid)
        gridout = yield motor.Op(alt.get, "foo")
        self.assertEqual(b("hello world"), (yield motor.Op(gridout.read)))

        yield motor.Op(alt.put, b(""), filename="mike")
        yield motor.Op(alt.put, b("foo"), filename="test")
        yield motor.Op(alt.put, b(""), filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield motor.Op(alt.list))))

    @gen_test
    def test_put_filelike(self):
        db = self.cx.pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)
        oid = yield motor.Op(fs.put, StringIO(b("hello world")), chunk_size=1)
        self.assertEqual(11, (yield motor.Op(db.fs.chunks.count)))
        gridout = yield motor.Op(fs.get, oid)
        self.assertEqual(b("hello world"), (yield motor.Op(gridout.read)))

    @gen_test
    def test_put_duplicate(self):
        db = self.cx.pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)
        oid = yield motor.Op(fs.put, b("hello"))
        with assert_raises(FileExists):
            yield motor.Op(fs.put, b("world"), _id=oid)


class TestGridfsReplicaSet(MotorReplicaSetTestBase):
    @gen_test
    def test_gridfs_replica_set(self):
        rsc = yield self.motor_rsc(
            w=self.w, wtimeout=5000,
            read_preference=ReadPreference.SECONDARY)

        fs = yield motor.Op(motor.MotorGridFS(rsc.pymongo_test).open)
        oid = yield motor.Op(fs.put, b('foo'))
        gridout = yield motor.Op(fs.get, oid)
        content = yield motor.Op(gridout.read)
        self.assertEqual(b('foo'), content)

    @gen_test
    def test_gridfs_secondary(self):
        primary_host, primary_port = self.primary
        primary_client = yield self.motor_client(primary_host, primary_port)

        secondary_host, secondary_port = self.secondaries[0]
        secondary_client = yield self.motor_client(
            secondary_host, secondary_port,
            read_preference=ReadPreference.SECONDARY)

        yield motor.Op(
            primary_client.pymongo_test.drop_collection, "fs.files")

        yield motor.Op(
            primary_client.pymongo_test.drop_collection, "fs.chunks")

        # Should detect it's connected to secondary and not attempt to
        # create index
        fs = yield motor.Op(
            motor.MotorGridFS(secondary_client.pymongo_test).open)

        # This won't detect secondary, raises error
        with assert_raises(AutoReconnect):
            yield motor.Op(fs.put, b('foo'))

    def tearDown(self):
        c = MongoClient(host, port)
        c.pymongo_test.drop_collection('fs.files')
        c.pymongo_test.drop_collection('fs.chunks')


if __name__ == "__main__":
    unittest.main()
