# -*- coding: utf-8 -*-
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

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest
from functools import partial
from bson import ObjectId

from gridfs.errors import FileExists, NoFile
from pymongo.errors import ConfigurationError
from tornado import gen
from tornado.testing import gen_test

import motor
from motor.motor_py3_compat import StringIO
from test.tornado_tests import MotorTest


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
    def test_basic(self):
        oid = yield self.fs.put(b"hello world")
        out = yield self.fs.get(oid)
        self.assertEqual(b"hello world", (yield out.read()))
        self.assertEqual(1, (yield self.db.fs.files.count()))
        self.assertEqual(1, (yield self.db.fs.chunks.count()))

        yield self.fs.delete(oid)
        with self.assertRaises(NoFile):
            yield self.fs.get(oid)

        self.assertEqual(0, (yield self.db.fs.files.count()))
        self.assertEqual(0, (yield self.db.fs.chunks.count()))

        with self.assertRaises(NoFile):
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
        with self.assertRaises(NoFile):
            yield alt.get(oid)

        self.assertEqual(0, (yield self.db.alt.files.count()))
        self.assertEqual(0, (yield self.db.alt.chunks.count()))

        with self.assertRaises(NoFile):
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

    @gen_test(timeout=30)
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
        with self.assertRaises(FileExists):
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
        with self.assertRaises(ConfigurationError):
            motor.MotorGridFS(client.motor_test)

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


if __name__ == "__main__":
    unittest.main()
