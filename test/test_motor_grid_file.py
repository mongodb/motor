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

import datetime
import unittest
from functools import partial

from bson.objectid import ObjectId
from bson.py3compat import b
from gridfs.errors import NoFile

import motor
from test import host, port, MotorTest, async_test_engine, AssertRaises


class MotorGridFileTest(MotorTest):
    def _reset(self):
        self.sync_db.drop_collection("fs.files")
        self.sync_db.drop_collection("fs.chunks")
        self.sync_db.drop_collection("alt.files")
        self.sync_db.drop_collection("alt.chunks")

    def setUp(self):
        super(MotorGridFileTest, self).setUp()
        self._reset()

    def tearDown(self):
        self._reset()
        super(MotorGridFileTest, self).tearDown()

    @async_test_engine(timeout_sec=20)
    def test_grid_in_callback(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        f = motor.MotorGridIn(db.fs, filename="test")
        yield motor.Op(self.check_optional_callback, f.open)
        f = yield motor.Op(motor.MotorGridIn(db.fs, filename="test").open)
        yield motor.Op(
            self.check_optional_callback, partial(f.set, 'name', 'value'))

        yield motor.Op(self.check_optional_callback, partial(f.write, b('a')))
        yield motor.Op(
            self.check_optional_callback, partial(f.writelines, [b('a')]))

        yield motor.Op(self.check_optional_callback, f.close)

        done()

    @async_test_engine()
    def test_grid_out_callback(self, done):
        # Some setup: we need to make an open GridOut
        db = self.motor_client(host, port).open_sync().pymongo_test
        f = yield motor.Op(motor.MotorGridIn(db.fs, filename="test").open)
        yield motor.Op(f.close)

        g = motor.MotorGridOut(db.fs, f._id)
        yield motor.Op(self.check_optional_callback, g.open)

        g = yield motor.Op(motor.MotorGridOut(db.fs, f._id).open)
        yield motor.Op(self.check_required_callback, g.read)
        yield motor.Op(self.check_required_callback, g.readline)
        done()

    @async_test_engine()
    def test_basic(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        f = yield motor.Op(motor.MotorGridIn(db.fs, filename="test").open)
        yield motor.Op(f.write, b("hello world"))
        yield motor.Op(f.close)
        self.assertEqual(1, (yield motor.Op(db.fs.files.find().count)))
        self.assertEqual(1, (yield motor.Op(db.fs.chunks.find().count)))

        g = yield motor.Op(motor.MotorGridOut(db.fs, f._id).open)
        self.assertEqual(b("hello world"), (yield motor.Op(g.read)))

        # make sure it's still there...
        g = yield motor.Op(motor.MotorGridOut(db.fs, f._id).open)
        self.assertEqual(b("hello world"), (yield motor.Op(g.read)))

        f = yield motor.Op(motor.MotorGridIn(db.fs, filename="test").open)
        yield motor.Op(f.close)
        self.assertEqual(2, (yield motor.Op(db.fs.files.find().count)))
        self.assertEqual(1, (yield motor.Op(db.fs.chunks.find().count)))

        g = yield motor.Op(motor.MotorGridOut(db.fs, f._id).open)
        self.assertEqual(b(""), (yield motor.Op(g.read)))
        done()

    @async_test_engine()
    def test_alternate_collection(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        yield motor.Op(db.alt.files.remove)
        yield motor.Op(db.alt.chunks.remove)

        f = yield motor.Op(motor.MotorGridIn(db.alt).open)
        yield motor.Op(f.write, b("hello world"))
        yield motor.Op(f.close)

        self.assertEqual(1, (yield motor.Op(db.alt.files.find().count)))
        self.assertEqual(1, (yield motor.Op(db.alt.chunks.find().count)))

        g = yield motor.Op(motor.MotorGridOut(db.alt, f._id).open)
        self.assertEqual(b("hello world"), (yield motor.Op(g.read)))

        # test that md5 still works...
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", g.md5)
        done()

    @async_test_engine()
    def test_grid_in_default_opts(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        a = yield motor.Op(motor.MotorGridIn(db.fs).open)

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual(None, a.filename)

        # This raises AttributeError because you can't directly set properties
        # in Motor, have to use set()
        def setter():
            a.filename = "my_file"
        self.assertRaises(AttributeError, setter)

        # This method of setting attributes works in Motor
        yield motor.Op(a.set, "filename", "my_file")
        self.assertEqual("my_file", a.filename)

        self.assertEqual(None, a.content_type)
        yield motor.Op(a.set, "content_type", "text/html")
        self.assertEqual("text/html", a.content_type)

        self.assertRaises(AttributeError, getattr, a, "length")
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(256 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertRaises(AttributeError, getattr, a, "upload_date")
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertRaises(AttributeError, getattr, a, "aliases")
        yield motor.Op(a.set, "aliases", ["foo"])
        self.assertEqual(["foo"], a.aliases)

        self.assertRaises(AttributeError, getattr, a, "metadata")
        yield motor.Op(a.set, "metadata", {"foo": 1})
        self.assertEqual({"foo": 1}, a.metadata)

        self.assertRaises(AttributeError, getattr, a, "md5")
        self.assertRaises(AttributeError, setattr, a, "md5", 5)

        yield motor.Op(a.close)

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual("my_file", a.filename)

        self.assertEqual("text/html", a.content_type)

        self.assertEqual(0, a.length)
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(256 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertTrue(isinstance(a.upload_date, datetime.datetime))
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertEqual(["foo"], a.aliases)

        self.assertEqual({"foo": 1}, a.metadata)

        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", a.md5)
        self.assertRaises(AttributeError, setattr, a, "md5", 5)
        done()

    @async_test_engine()
    def test_grid_in_custom_opts(self, done):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        db = self.motor_client(host, port).open_sync().pymongo_test
        a = yield motor.Op(
            motor.MotorGridIn(db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello").open)

        self.assertEqual(5, a._id)
        self.assertEqual("my_file", a.filename)
        self.assertEqual("text/html", a.content_type)
        self.assertEqual(1000, a.chunk_size)
        self.assertEqual(["foo"], a.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, a.metadata)
        self.assertEqual(3, a.bar)
        self.assertEqual("hello", a.baz)
        self.assertRaises(AttributeError, getattr, a, "mike")

        b = yield motor.Op(
            motor.MotorGridIn(db.fs,
            content_type="text/html", chunk_size=1000, baz=100).open)
        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)
        done()

    @async_test_engine()
    def test_grid_out_default_opts(self, done):
        self.assertRaises(TypeError, motor.MotorGridOut, "foo")

        db = self.motor_client(host, port).open_sync().pymongo_test
        gout = motor.MotorGridOut(db.fs, 5)
        yield AssertRaises(NoFile, gout.open)

        a = yield motor.Op(motor.MotorGridIn(db.fs).open)
        yield motor.Op(a.close)

        b = yield motor.Op(motor.MotorGridOut(db.fs, a._id).open)

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(256 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)
        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", b.md5)

        for attr in ["_id", "name", "content_type", "length", "chunk_size",
                     "upload_date", "aliases", "metadata", "md5"]:
            self.assertRaises(AttributeError, setattr, b, attr, 5)

        done()

    @async_test_engine()
    def test_grid_out_custom_opts(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        one = yield motor.Op(
            motor.MotorGridIn(db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello").open)
        yield motor.Op(one.write, b("hello world"))
        yield motor.Op(one.close)

        two = yield motor.Op(motor.MotorGridOut(db.fs, 5).open)

        self.assertEqual(5, two._id)
        self.assertEqual(11, two.length)
        self.assertEqual("text/html", two.content_type)
        self.assertEqual(1000, two.chunk_size)
        self.assertTrue(isinstance(two.upload_date, datetime.datetime))
        self.assertEqual(["foo"], two.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, two.metadata)
        self.assertEqual(3, two.bar)
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", two.md5)

        for attr in ["_id", "name", "content_type", "length", "chunk_size",
                     "upload_date", "aliases", "metadata", "md5"]:
            self.assertRaises(AttributeError, setattr, two, attr, 5)

        done()

    @async_test_engine()
    def test_grid_out_file_document(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        one = yield motor.Op(motor.MotorGridIn(db.fs).open)
        yield motor.Op(one.write, b("foo bar"))
        yield motor.Op(one.close)

        two = yield motor.Op(motor.MotorGridOut(
            db.fs,
            file_document=(yield motor.Op(db.fs.files.find_one))).open)

        self.assertEqual(b("foo bar"), (yield motor.Op(two.read)))

        three = yield motor.Op(motor.MotorGridOut(
            db.fs, 5,
            file_document=(yield motor.Op(db.fs.files.find_one))).open)

        self.assertEqual(b("foo bar"), (yield motor.Op(three.read)))

        yield AssertRaises(
            NoFile, motor.MotorGridOut(db.fs, file_document={}).open)
        done()

    @async_test_engine()
    def test_write_file_like(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        one = yield motor.Op(motor.MotorGridIn(db.fs).open)
        yield motor.Op(one.write, b("hello world"))
        yield motor.Op(one.close)

        two = yield motor.Op(motor.MotorGridOut(db.fs, one._id).open)

        three = yield motor.Op(motor.MotorGridIn(db.fs).open)
        yield motor.Op(three.write, two)
        yield motor.Op(three.close)

        four = yield motor.Op(motor.MotorGridOut(db.fs, three._id).open)
        self.assertEqual(b("hello world"), (yield motor.Op(four.read)))
        done()

    @async_test_engine()
    def test_set_after_close(self, done):
        db = self.motor_client(host, port).open_sync().pymongo_test
        f = yield motor.Op(
            motor.MotorGridIn(db.fs, _id="foo", bar="baz").open)

        self.assertEqual("foo", f._id)
        self.assertEqual("baz", f.bar)
        self.assertRaises(AttributeError, getattr, f, "baz")
        self.assertRaises(AttributeError, getattr, f, "uploadDate")

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        f.bar = "foo"
        f.baz = 5

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertRaises(AttributeError, getattr, f, "uploadDate")

        yield motor.Op(f.close)

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertTrue(f.uploadDate)

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        yield motor.Op(f.set, "bar", "a")
        yield motor.Op(f.set, "baz", "b")
        self.assertRaises(AttributeError, setattr, f, "upload_date", 5)

        g = yield motor.Op(motor.MotorGridOut(db.fs, f._id).open)
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)
        # Versions 2.0.1 and older saved a _closed field for some reason.
        self.assertRaises(AttributeError, getattr, g, "_closed")
        done()

    @async_test_engine()
    def test_stream_to_handler(self, done):
        class MockRequestHandler(object):
            def __init__(self):
                self.n_written = 0

            def write(self, data):
                self.n_written += len(data)

            def flush(self):
                pass

        db = self.motor_client(host, port).open_sync().pymongo_test
        fs = yield motor.Op(motor.MotorGridFS(db).open)

        for content_length in (0, 1, 100, 100 * 1000):
            _id = yield motor.Op(fs.put, b('a') * content_length)
            gridout = yield motor.Op(fs.get, _id)
            handler = MockRequestHandler()
            yield motor.Op(gridout.stream_to_handler, handler)
            self.assertEqual(content_length, handler.n_written)
            yield motor.Op(fs.delete, _id)

        done()

if __name__ == "__main__":
    unittest.main()
