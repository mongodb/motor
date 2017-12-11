# -*- coding: utf-8 -*-
# Copyright 2014 MongoDB, Inc.
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

"""Test AsyncIOMotorGridFS."""

import asyncio
import datetime
import sys
import traceback
import unittest

from pymongo.errors import InvalidOperation, ConfigurationError

import test
from gridfs.errors import FileExists, NoFile
from motor.motor_asyncio import (AsyncIOMotorGridFS,
                                 AsyncIOMotorGridIn,
                                 AsyncIOMotorGridOut)
from motor.motor_py3_compat import StringIO
from test.asyncio_tests import asyncio_test, AsyncIOTestCase


class TestAsyncIOGridFile(AsyncIOTestCase):
    @asyncio.coroutine
    def _reset(self):
        yield from self.db.drop_collection("fs.files")
        yield from self.db.drop_collection("fs.chunks")
        yield from self.db.drop_collection("alt.files")
        yield from self.db.drop_collection("alt.chunks")

    def tearDown(self):
        self.loop.run_until_complete(self._reset())
        super(TestAsyncIOGridFile, self).tearDown()

    @asyncio_test
    def test_attributes(self):
        f = AsyncIOMotorGridIn(
            self.db.fs,
            filename="test",
            foo="bar",
            content_type="text")

        yield from f.close()

        g = AsyncIOMotorGridOut(self.db.fs, f._id)
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

        yield from g.open()
        for attr_name in attr_names:
            getattr(g, attr_name)

    @asyncio_test
    def test_gridout_open_exc_info(self):
        g = AsyncIOMotorGridOut(self.db.fs, "_id that doesn't exist")
        try:
            yield from g.open()
        except NoFile:
            _, _, tb = sys.exc_info()
            # The call tree should include PyMongo code we ran on a thread.
            formatted = '\n'.join(traceback.format_tb(tb))
            self.assertTrue('_ensure_file' in formatted)

    @asyncio_test
    def test_alternate_collection(self):
        yield from self.db.alt.files.delete_many({})
        yield from self.db.alt.chunks.delete_many({})

        f = AsyncIOMotorGridIn(self.db.alt)
        yield from f.write(b"hello world")
        yield from f.close()

        self.assertEqual(1, (yield from self.db.alt.files.find().count()))
        self.assertEqual(1, (yield from self.db.alt.chunks.find().count()))

        g = AsyncIOMotorGridOut(self.db.alt, f._id)
        self.assertEqual(b"hello world", (yield from g.read()))

        # test that md5 still works...
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", g.md5)

    @asyncio_test
    def test_grid_in_custom_opts(self):
        self.assertRaises(TypeError, AsyncIOMotorGridIn, "foo")
        a = AsyncIOMotorGridIn(
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

        b = AsyncIOMotorGridIn(
            self.db.fs,
            content_type="text/html",
            chunk_size=1000,
            baz=100)

        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)

    @asyncio_test
    def test_grid_out_default_opts(self):
        self.assertRaises(TypeError, AsyncIOMotorGridOut, "foo")
        gout = AsyncIOMotorGridOut(self.db.fs, 5)
        with self.assertRaises(NoFile):
            yield from gout.open()

        a = AsyncIOMotorGridIn(self.db.fs)
        yield from a.close()

        b = yield from AsyncIOMotorGridOut(self.db.fs, a._id).open()

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(255 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)
        self.assertEqual("d41d8cd98f00b204e9800998ecf8427e", b.md5)

    @asyncio_test
    def test_grid_out_custom_opts(self):
        one = AsyncIOMotorGridIn(
            self.db.fs, _id=5, filename="my_file",
            contentType="text/html", chunkSize=1000, aliases=["foo"],
            metadata={"foo": 1, "bar": 2}, bar=3, baz="hello")

        yield from one.write(b"hello world")
        yield from one.close()

        two = yield from AsyncIOMotorGridOut(self.db.fs, 5).open()

        self.assertEqual(5, two._id)
        self.assertEqual(11, two.length)
        self.assertEqual("text/html", two.content_type)
        self.assertEqual(1000, two.chunk_size)
        self.assertTrue(isinstance(two.upload_date, datetime.datetime))
        self.assertEqual(["foo"], two.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, two.metadata)
        self.assertEqual(3, two.bar)
        self.assertEqual("5eb63bbbe01eeed093cb22bb8f5acdc3", two.md5)

    @asyncio_test
    def test_grid_out_file_document(self):
        one = AsyncIOMotorGridIn(self.db.fs)
        yield from one.write(b"foo bar")
        yield from one.close()

        file_document = yield from self.db.fs.files.find_one()
        two = AsyncIOMotorGridOut(
            self.db.fs, file_document=file_document)

        self.assertEqual(b"foo bar", (yield from two.read()))

        file_document = yield from self.db.fs.files.find_one()
        three = AsyncIOMotorGridOut(self.db.fs, 5, file_document)
        self.assertEqual(b"foo bar", (yield from three.read()))

        gridout = AsyncIOMotorGridOut(self.db.fs, file_document={})
        with self.assertRaises(NoFile):
            yield from gridout.open()

    @asyncio_test
    def test_write_file_like(self):
        one = AsyncIOMotorGridIn(self.db.fs)
        yield from one.write(b"hello world")
        yield from one.close()

        two = AsyncIOMotorGridOut(self.db.fs, one._id)
        three = AsyncIOMotorGridIn(self.db.fs)
        yield from three.write(two)
        yield from three.close()

        four = AsyncIOMotorGridOut(self.db.fs, three._id)
        self.assertEqual(b"hello world", (yield from four.read()))

    @asyncio_test
    def test_set_after_close(self):
        f = AsyncIOMotorGridIn(self.db.fs, _id="foo", bar="baz")

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

        yield from f.close()

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertTrue(f.uploadDate)

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        yield from f.set("bar", "a")
        yield from f.set("baz", "b")
        self.assertRaises(AttributeError, setattr, f, "upload_date", 5)

        g = yield from AsyncIOMotorGridOut(self.db.fs, f._id).open()
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)

    @asyncio_test
    def test_stream_to_handler(self):
        fs = AsyncIOMotorGridFS(self.db)

        for content_length in (0, 1, 100, 100 * 1000):
            _id = yield from fs.put(b'a' * content_length)
            gridout = yield from fs.get(_id)
            handler = test.MockRequestHandler()
            yield from gridout.stream_to_handler(handler)
            self.assertEqual(content_length, handler.n_written)
            yield from fs.delete(_id)


class TestAsyncIOGridFS(AsyncIOTestCase):
    @asyncio.coroutine
    def _reset(self):
        yield from self.db.drop_collection("fs.files")
        yield from self.db.drop_collection("fs.chunks")
        yield from self.db.drop_collection("alt.files")
        yield from self.db.drop_collection("alt.chunks")

    def setUp(self):
        super().setUp()
        self.loop.run_until_complete(self._reset())
        self.fs = AsyncIOMotorGridFS(self.db)

    def tearDown(self):
        self.loop.run_until_complete(self._reset())
        super().tearDown()

    @asyncio_test
    def test_get_version(self):
        # new_file creates a MotorGridIn.
        gin = yield from self.fs.new_file(_id=1, filename='foo', field=0)
        yield from gin.write(b'a')
        yield from gin.close()

        yield from self.fs.put(b'', filename='foo', field=1)
        yield from self.fs.put(b'', filename='foo', field=2)

        gout = yield from self.fs.get_version('foo')
        self.assertEqual(2, gout.field)
        gout = yield from self.fs.get_version('foo', -3)
        self.assertEqual(0, gout.field)

        gout = yield from self.fs.get_last_version('foo')
        self.assertEqual(2, gout.field)

    @asyncio_test
    def test_basic(self):
        oid = yield from self.fs.put(b"hello world")
        out = yield from self.fs.get(oid)
        self.assertEqual(b"hello world", (yield from out.read()))
        self.assertEqual(1, (yield from self.db.fs.files.count()))
        self.assertEqual(1, (yield from self.db.fs.chunks.count()))

        yield from self.fs.delete(oid)
        with self.assertRaises(NoFile):
            yield from self.fs.get(oid)

        self.assertEqual(0, (yield from self.db.fs.files.count()))
        self.assertEqual(0, (yield from self.db.fs.chunks.count()))

        with self.assertRaises(NoFile):
            yield from self.fs.get("foo")

        self.assertEqual(
            "foo", (yield from self.fs.put(b"hello world", _id="foo")))

        gridout = yield from self.fs.get("foo")
        self.assertEqual(b"hello world", (yield from gridout.read()))

    @asyncio_test
    def test_list(self):
        self.assertEqual([], (yield from self.fs.list()))
        yield from self.fs.put(b"hello world")
        self.assertEqual([], (yield from self.fs.list()))

        yield from self.fs.put(b"", filename="mike")
        yield from self.fs.put(b"foo", filename="test")
        yield from self.fs.put(b"", filename="hello world")

        self.assertEqual(set(["mike", "test", "hello world"]),
                         set((yield from self.fs.list())))

    @asyncio_test(timeout=30)
    def test_put_filelike(self):
        oid = yield from self.fs.put(StringIO(b"hello world"), chunk_size=1)
        self.assertEqual(11, (yield from self.cx.motor_test.fs.chunks.count()))
        gridout = yield from self.fs.get(oid)
        self.assertEqual(b"hello world", (yield from gridout.read()))

    @asyncio_test
    def test_put_duplicate(self):
        oid = yield from self.fs.put(b"hello")
        with self.assertRaises(FileExists):
            yield from self.fs.put(b"world", _id=oid)

    @asyncio_test
    def test_put_unacknowledged(self):
        client = self.asyncio_client(w=0)
        with self.assertRaises(ConfigurationError):
            AsyncIOMotorGridFS(client.motor_test)

        client.close()

    @asyncio_test
    def test_gridfs_find(self):
        yield from self.fs.put(b"test2", filename="two")
        yield from self.fs.put(b"test2+", filename="two")
        yield from self.fs.put(b"test1", filename="one")
        yield from self.fs.put(b"test2++", filename="two")
        cursor = self.fs.find().sort("_id", -1).skip(1).limit(2)
        self.assertTrue((yield from cursor.fetch_next))
        grid_out = cursor.next_object()
        self.assertTrue(isinstance(grid_out, AsyncIOMotorGridOut))
        self.assertEqual(b"test1", (yield from grid_out.read()))
        self.assertRaises(TypeError, self.fs.find, {}, {"_id": True})


if __name__ == "__main__":
    unittest.main()
