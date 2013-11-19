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
from tornado.testing import gen_test
from pymongo.errors import InvalidOperation

import motor
from test import MotorTest, assert_raises


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

    @gen_test
    def test_grid_in_callback(self):
        db = self.cx.pymongo_test
        f = motor.MotorGridIn(db.fs, filename="test")
        yield self.check_optional_callback(f.open)
        f = yield motor.MotorGridIn(db.fs, filename="test").open()
        yield self.check_optional_callback(partial(f.set, 'name', 'value'))

        yield self.check_optional_callback(partial(f.write, b('a')))
        yield self.check_optional_callback(partial(f.writelines, [b('a')]))

        self.assertRaises(TypeError, f.close, callback='foo')
        self.assertRaises(TypeError, f.close, callback=1)
        f.close(callback=None)  # No error

    @gen_test
    def test_grid_out_callback(self):
        # Some setup: we need to make a GridOut.
        db = self.cx.pymongo_test
        f = yield motor.MotorGridIn(db.fs, filename="test").open()
        yield f.close()

        g = motor.MotorGridOut(db.fs, f._id)
        yield self.check_optional_callback(g.open)

        g = yield motor.MotorGridOut(db.fs, f._id).open()
        yield self.check_optional_callback(g.read)
        yield self.check_optional_callback(g.readline)

    @gen_test
    def test_attributes(self):
        db = self.cx.pymongo_test
        f = yield motor.MotorGridIn(
            db.fs, filename="test", foo="bar", content_type="text").open()

        yield f.close()

        g = motor.MotorGridOut(db.fs, f._id)
        attr_names = (
            '_id',
            'filename',
            'name',
            'name',
            'content_type',
            'length',
            'chunk_size',
            'upload_date',
            'aliases',
            'metadata',
            'md5')

        for attr_name in attr_names:
            self.assertRaises(InvalidOperation, getattr, g, attr_name)

        yield g.open()
        for attr_name in attr_names:
            getattr(g, attr_name)

    @gen_test
    def test_iteration(self):
        db = self.cx.pymongo_test
        fs = yield motor.MotorGridFS(db).open()
        _id = yield fs.put('foo')
        g = motor.MotorGridOut(db.fs, _id)

        # Iteration is prohibited.
        self.assertRaises(TypeError, iter, g)

    @gen_test
    def test_basic(self):
        db = self.cx.pymongo_test
        f = yield motor.MotorGridIn(db.fs, filename="test").open()
        yield f.write(b("hello world"))
        yield f.close()
        self.assertEqual(1, (yield db.fs.files.find().count()))
        self.assertEqual(1, (yield db.fs.chunks.find().count()))

        g = motor.MotorGridOut(db.fs, f._id)
        self.assertEqual(b("hello world"), (yield g.read()))

        f = yield motor.MotorGridIn(db.fs, filename="test").open()
        yield f.close()
        self.assertEqual(2, (yield db.fs.files.find().count()))
        self.assertEqual(1, (yield db.fs.chunks.find().count()))

        g = motor.MotorGridOut(db.fs, f._id)
        self.assertEqual(b(""), (yield g.read()))

    @gen_test
    def test_alternate_collection(self):
        db = self.cx.pymongo_test
        yield db.alt.files.remove()
        yield db.alt.chunks.remove()

        f = yield motor.MotorGridIn(db.alt).open()
        yield f.write(b("hello world"))
        yield f.close()

        self.assertEqual(1, (yield db.alt.files.find().count()))
        self.assertEqual(1, (yield db.alt.chunks.find().count()))

        g = motor.MotorGridOut(db.alt, f._id)
        self.assertEqual(b("hello world"), (yield g.read()))

        # test that md5 still works...
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", g.md5)

    @gen_test
    def test_grid_in_default_opts(self):
        db = self.cx.pymongo_test
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        a = yield motor.MotorGridIn(db.fs).open()

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual(None, a.filename)

        # This raises AttributeError because you can't directly set properties
        # in Motor, have to use set()
        def setter():
            a.filename = "my_file"
        self.assertRaises(AttributeError, setter)

        # This method of setting attributes works in Motor
        yield a.set("filename", "my_file")
        self.assertEqual("my_file", a.filename)

        self.assertEqual(None, a.content_type)
        yield a.set("content_type", "text/html")
        self.assertEqual("text/html", a.content_type)

        self.assertRaises(AttributeError, getattr, a, "length")
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(256 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertRaises(AttributeError, getattr, a, "upload_date")
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertRaises(AttributeError, getattr, a, "aliases")
        yield a.set("aliases", ["foo"])
        self.assertEqual(["foo"], a.aliases)

        self.assertRaises(AttributeError, getattr, a, "metadata")
        yield a.set("metadata", {"foo": 1})
        self.assertEqual({"foo": 1}, a.metadata)

        self.assertRaises(AttributeError, getattr, a, "md5")
        self.assertRaises(AttributeError, setattr, a, "md5", 5)

        yield a.close()

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

    @gen_test
    def test_grid_in_custom_opts(self):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        db = self.cx.pymongo_test
        a = yield motor.MotorGridIn(
            db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello"
        ).open()

        self.assertEqual(5, a._id)
        self.assertEqual("my_file", a.filename)
        self.assertEqual("text/html", a.content_type)
        self.assertEqual(1000, a.chunk_size)
        self.assertEqual(["foo"], a.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, a.metadata)
        self.assertEqual(3, a.bar)
        self.assertEqual("hello", a.baz)
        self.assertRaises(AttributeError, getattr, a, "mike")

        b = yield motor.MotorGridIn(
            db.fs, content_type="text/html", chunk_size=1000, baz=100).open()

        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)

    @gen_test
    def test_grid_out_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridOut, "foo")

        db = self.cx.pymongo_test
        gout = motor.MotorGridOut(db.fs, 5)
        with assert_raises(NoFile):
            yield gout.open()

        a = yield motor.MotorGridIn(db.fs).open()
        yield a.close()

        b = yield motor.MotorGridOut(db.fs, a._id).open()

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(256 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)
        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", b.md5)

    @gen_test
    def test_grid_out_custom_opts(self):
        db = self.cx.pymongo_test

        one = yield motor.MotorGridIn(
            db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello"
        ).open()

        yield one.write(b("hello world"))
        yield one.close()

        two = yield motor.MotorGridOut(db.fs, 5).open()

        self.assertEqual(5, two._id)
        self.assertEqual(11, two.length)
        self.assertEqual("text/html", two.content_type)
        self.assertEqual(1000, two.chunk_size)
        self.assertTrue(isinstance(two.upload_date, datetime.datetime))
        self.assertEqual(["foo"], two.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, two.metadata)
        self.assertEqual(3, two.bar)
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", two.md5)

    @gen_test
    def test_grid_out_file_document(self):
        db = self.cx.pymongo_test
        one = yield motor.MotorGridIn(db.fs).open()
        yield one.write(b("foo bar"))
        yield one.close()

        file_document = yield db.fs.files.find_one()
        two = motor.MotorGridOut(db.fs, file_document=file_document)
        self.assertEqual(b("foo bar"), (yield two.read()))

        file_document = yield db.fs.files.find_one()
        three = motor.MotorGridOut(db.fs, 5, file_document)
        self.assertEqual(b("foo bar"), (yield three.read()))

        with assert_raises(NoFile):
            yield motor.MotorGridOut(db.fs, file_document={}).open()

    @gen_test
    def test_write_file_like(self):
        db = self.cx.pymongo_test
        one = yield motor.MotorGridIn(db.fs).open()
        yield one.write(b("hello world"))
        yield one.close()

        two = motor.MotorGridOut(db.fs, one._id)
        three = yield motor.MotorGridIn(db.fs).open()
        yield three.write(two)
        yield three.close()

        four = motor.MotorGridOut(db.fs, three._id)
        self.assertEqual(b("hello world"), (yield four.read()))

    @gen_test
    def test_set_after_close(self):
        db = self.cx.pymongo_test
        f = yield motor.MotorGridIn(db.fs, _id="foo", bar="baz").open()

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

        yield f.close()

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertTrue(f.uploadDate)

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        yield f.set("bar", "a")
        yield f.set("baz", "b")
        self.assertRaises(AttributeError, setattr, f, "upload_date", 5)

        g = yield motor.MotorGridOut(db.fs, f._id).open()
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)
        # Versions 2.0.1 and older saved a _closed field for some reason.
        self.assertRaises(AttributeError, getattr, g, "_closed")

    @gen_test
    def test_stream_to_handler(self):
        class MockRequestHandler(object):
            def __init__(self):
                self.n_written = 0

            def write(self, data):
                self.n_written += len(data)

            def flush(self):
                pass

        db = self.cx.pymongo_test
        fs = yield motor.MotorGridFS(db).open()

        for content_length in (0, 1, 100, 100 * 1000):
            _id = yield fs.put(b('a') * content_length)
            gridout = yield fs.get(_id)
            handler = MockRequestHandler()
            yield gridout.stream_to_handler(handler)
            self.assertEqual(content_length, handler.n_written)
            yield fs.delete(_id)

if __name__ == "__main__":
    unittest.main()
