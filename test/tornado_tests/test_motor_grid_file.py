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

import datetime
import sys
import traceback
import unittest

from bson.objectid import ObjectId
from gridfs.errors import NoFile
from tornado import gen
from tornado.testing import gen_test
from pymongo.errors import InvalidOperation

import motor
from test import MockRequestHandler, SkipTest
from test.tornado_tests import MotorTest


class MotorGridFileTest(MotorTest):
    @gen.coroutine
    def _reset(self):
        yield self.db.drop_collection("fs.files")
        yield self.db.drop_collection("fs.chunks")
        yield self.db.drop_collection("alt.files")
        yield self.db.drop_collection("alt.chunks")

    def tearDown(self):
        self.io_loop.run_sync(self._reset)
        super(MotorGridFileTest, self).tearDown()

    @gen_test
    def test_attributes(self):
        f = motor.MotorGridIn(
            self.db.fs,
            filename="test",
            foo="bar",
            content_type="text")

        yield f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)
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
        fs = motor.MotorGridFS(self.db)
        _id = yield fs.put(b'foo')
        g = motor.MotorGridOut(self.db.fs, _id)

        # Iteration is prohibited.
        self.assertRaises(TypeError, iter, g)

    @gen_test
    def test_basic(self):
        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield f.write(b"hello world")
        yield f.close()
        self.assertEqual(1, (yield self.db.fs.files.find().count()))
        self.assertEqual(1, (yield self.db.fs.chunks.find().count()))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"hello world", (yield g.read()))

        f = motor.MotorGridIn(self.db.fs, filename="test")
        yield f.close()
        self.assertEqual(2, (yield self.db.fs.files.find().count()))
        self.assertEqual(1, (yield self.db.fs.chunks.find().count()))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"", (yield g.read()))

    @gen_test
    def test_readchunk(self):
        in_data = b'a' * 10
        f = motor.MotorGridIn(self.db.fs, chunkSize=3)
        yield f.write(in_data)
        yield f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)

        # This is starting to look like Lisp.
        self.assertEqual(3, len((yield g.readchunk())))

        self.assertEqual(2, len((yield g.read(2))))
        self.assertEqual(1, len((yield g.readchunk())))

        self.assertEqual(3, len((yield g.read(3))))

        self.assertEqual(1, len((yield g.readchunk())))

        self.assertEqual(0, len((yield g.readchunk())))

    @gen_test
    def test_gridout_open_exc_info(self):
        if sys.version_info < (3, ):
            raise SkipTest("Requires Python 3")

        g = motor.MotorGridOut(self.db.fs, "_id that doesn't exist")
        try:
            yield g.open()
        except NoFile:
            _, _, tb = sys.exc_info()

            # The call tree should include PyMongo code we ran on a thread.
            formatted = '\n'.join(traceback.format_tb(tb))
            self.assertTrue('_ensure_file' in formatted)

    @gen_test
    def test_alternate_collection(self):
        yield self.db.alt.files.delete_many({})
        yield self.db.alt.chunks.delete_many({})

        f = motor.MotorGridIn(self.db.alt)
        yield f.write(b"hello world")
        yield f.close()

        self.assertEqual(1, (yield self.db.alt.files.find().count()))
        self.assertEqual(1, (yield self.db.alt.chunks.find().count()))

        g = motor.MotorGridOut(self.db.alt, f._id)
        self.assertEqual(b"hello world", (yield g.read()))

        # test that md5 still works...
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", g.md5)

    @gen_test
    def test_grid_in_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")

        a = motor.MotorGridIn(self.db.fs)

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

        self.assertEqual(255 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertRaises(AttributeError, getattr, a, "upload_date")
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertRaises(AttributeError, getattr, a, "aliases")
        yield a.set("aliases", ["foo"])
        self.assertEqual(["foo"], a.aliases)

        self.assertRaises(AttributeError, getattr, a, "metadata")
        yield a.set("metadata", {"foo": 1})
        self.assertEqual({"foo": 1}, a.metadata)

        self.assertRaises(AttributeError, setattr, a, "md5", 5)

        yield a.close()

        self.assertTrue(isinstance(a._id, ObjectId))
        self.assertRaises(AttributeError, setattr, a, "_id", 5)

        self.assertEqual("my_file", a.filename)

        self.assertEqual("text/html", a.content_type)

        self.assertEqual(0, a.length)
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(255 * 1024, a.chunk_size)
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
        a = motor.MotorGridIn(
            self.db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello")

        self.assertEqual(5, a._id)
        self.assertEqual("my_file", a.filename)
        self.assertEqual("text/html", a.content_type)
        self.assertEqual(1000, a.chunk_size)
        self.assertEqual(["foo"], a.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, a.metadata)
        self.assertEqual(3, a.bar)
        self.assertEqual("hello", a.baz)
        self.assertRaises(AttributeError, getattr, a, "mike")

        b = motor.MotorGridIn(
            self.db.fs,
            content_type="text/html",
            chunk_size=1000,
            baz=100)

        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)

    @gen_test
    def test_grid_out_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridOut, "foo")
        gout = motor.MotorGridOut(self.db.fs, 5)
        with self.assertRaises(NoFile):
            yield gout.open()

        a = motor.MotorGridIn(self.db.fs)
        yield a.close()

        b = yield motor.MotorGridOut(self.db.fs, a._id).open()

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(255 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)
        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", b.md5)

    @gen_test
    def test_grid_out_custom_opts(self):
        one = motor.MotorGridIn(
            self.db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello")

        yield one.write(b"hello world")
        yield one.close()

        two = yield motor.MotorGridOut(self.db.fs, 5).open()

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
        one = motor.MotorGridIn(self.db.fs)
        yield one.write(b"foo bar")
        yield one.close()

        file_document = yield self.db.fs.files.find_one()
        two = motor.MotorGridOut(
            self.db.fs, file_document=file_document)

        self.assertEqual(b"foo bar", (yield two.read()))

        file_document = yield self.db.fs.files.find_one()
        three = motor.MotorGridOut(self.db.fs, 5, file_document)
        self.assertEqual(b"foo bar", (yield three.read()))

        gridout = motor.MotorGridOut(self.db.fs, file_document={})
        with self.assertRaises(NoFile):
            yield gridout.open()

    @gen_test
    def test_write_file_like(self):
        one = motor.MotorGridIn(self.db.fs)
        yield one.write(b"hello world")
        yield one.close()

        two = motor.MotorGridOut(self.db.fs, one._id)
        three = motor.MotorGridIn(self.db.fs)
        yield three.write(two)
        yield three.close()

        four = motor.MotorGridOut(self.db.fs, three._id)
        self.assertEqual(b"hello world", (yield four.read()))

    @gen_test
    def test_set_after_close(self):
        f = motor.MotorGridIn(self.db.fs, _id="foo", bar="baz")

        self.assertEqual("foo", f._id)
        self.assertEqual("baz", f.bar)
        self.assertRaises(AttributeError, getattr, f, "baz")
        self.assertRaises(AttributeError, getattr, f, "uploadDate")
        self.assertRaises(AttributeError, setattr, f, "_id", 5)

        f.bar = "foo"
        f.baz = 5

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

        g = yield motor.MotorGridOut(self.db.fs, f._id).open()
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)

    @gen_test
    def test_stream_to_handler(self):
        fs = motor.MotorGridFS(self.db)

        for content_length in (0, 1, 100, 100 * 1000):
            _id = yield fs.put(b'a' * content_length)
            gridout = yield fs.get(_id)
            handler = MockRequestHandler()
            yield gridout.stream_to_handler(handler)
            self.assertEqual(content_length, handler.n_written)
            yield fs.delete(_id)

if __name__ == "__main__":
    unittest.main()
