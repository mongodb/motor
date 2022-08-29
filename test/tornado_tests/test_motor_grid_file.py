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

"""Test GridFS with Motor, an asynchronous driver for MongoDB and Tornado."""

import datetime
import sys
import traceback
import unittest
from test import MockRequestHandler
from test.tornado_tests import MotorTest

from bson.objectid import ObjectId
from gridfs.errors import NoFile
from pymongo.errors import InvalidOperation
from tornado.testing import gen_test

import motor


class MotorGridFileTest(MotorTest):
    async def _reset(self):
        await self.db.drop_collection("fs.files")
        await self.db.drop_collection("fs.chunks")
        await self.db.drop_collection("alt.files")
        await self.db.drop_collection("alt.chunks")

    def tearDown(self):
        self.io_loop.run_sync(self._reset)
        super().tearDown()

    @gen_test
    async def test_attributes(self):
        f = motor.MotorGridIn(self.db.fs, filename="test", foo="bar", content_type="text")

        await f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)
        attr_names = (
            "_id",
            "filename",
            "name",
            "name",
            "content_type",
            "length",
            "chunk_size",
            "upload_date",
            "aliases",
            "metadata",
        )

        for attr_name in attr_names:
            self.assertRaises(InvalidOperation, getattr, g, attr_name)

        await g.open()
        for attr_name in attr_names:
            getattr(g, attr_name)

    @gen_test
    async def test_iteration(self):
        fs = motor.MotorGridFSBucket(self.db)
        _id = await fs.upload_from_stream("filename", b"foo")
        g = motor.MotorGridOut(self.db.fs, _id)

        # Iteration is prohibited.
        self.assertRaises(TypeError, iter, g)

    @gen_test
    async def test_basic(self):
        f = motor.MotorGridIn(self.db.fs, filename="test")
        await f.write(b"hello world")
        await f.close()
        self.assertEqual(1, (await self.db.fs.files.count_documents({})))
        self.assertEqual(1, (await self.db.fs.chunks.count_documents({})))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"hello world", (await g.read()))

        f = motor.MotorGridIn(self.db.fs, filename="test")
        await f.close()
        self.assertEqual(2, (await self.db.fs.files.count_documents({})))
        self.assertEqual(1, (await self.db.fs.chunks.count_documents({})))

        g = motor.MotorGridOut(self.db.fs, f._id)
        self.assertEqual(b"", (await g.read()))

    @gen_test
    async def test_readchunk(self):
        in_data = b"a" * 10
        f = motor.MotorGridIn(self.db.fs, chunkSize=3)
        await f.write(in_data)
        await f.close()

        g = motor.MotorGridOut(self.db.fs, f._id)

        # This is starting to look like Lisp.
        self.assertEqual(3, len((await g.readchunk())))

        self.assertEqual(2, len((await g.read(2))))
        self.assertEqual(1, len((await g.readchunk())))

        self.assertEqual(3, len((await g.read(3))))

        self.assertEqual(1, len((await g.readchunk())))

        self.assertEqual(0, len((await g.readchunk())))

    @gen_test
    async def test_gridout_open_exc_info(self):
        g = motor.MotorGridOut(self.db.fs, "_id that doesn't exist")
        try:
            await g.open()
        except NoFile:
            _, _, tb = sys.exc_info()

            # The call tree should include PyMongo code we ran on a thread.
            formatted = "\n".join(traceback.format_tb(tb))
            self.assertTrue("_ensure_file" in formatted)

    @gen_test
    async def test_alternate_collection(self):
        await self.db.alt.files.delete_many({})
        await self.db.alt.chunks.delete_many({})

        f = motor.MotorGridIn(self.db.alt)
        await f.write(b"hello world")
        await f.close()

        self.assertEqual(1, (await self.db.alt.files.count_documents({})))
        self.assertEqual(1, (await self.db.alt.chunks.count_documents({})))

        g = motor.MotorGridOut(self.db.alt, f._id)
        self.assertEqual(b"hello world", (await g.read()))

    @gen_test
    async def test_grid_in_default_opts(self):
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
        await a.set("filename", "my_file")
        self.assertEqual("my_file", a.filename)

        self.assertEqual(None, a.content_type)
        await a.set("content_type", "text/html")
        self.assertEqual("text/html", a.content_type)

        self.assertRaises(AttributeError, getattr, a, "length")
        self.assertRaises(AttributeError, setattr, a, "length", 5)

        self.assertEqual(255 * 1024, a.chunk_size)
        self.assertRaises(AttributeError, setattr, a, "chunk_size", 5)

        self.assertRaises(AttributeError, getattr, a, "upload_date")
        self.assertRaises(AttributeError, setattr, a, "upload_date", 5)

        self.assertRaises(AttributeError, getattr, a, "aliases")
        await a.set("aliases", ["foo"])
        self.assertEqual(["foo"], a.aliases)

        self.assertRaises(AttributeError, getattr, a, "metadata")
        await a.set("metadata", {"foo": 1})
        self.assertEqual({"foo": 1}, a.metadata)

        await a.close()

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

    @gen_test
    async def test_grid_in_custom_opts(self):
        self.assertRaises(TypeError, motor.MotorGridIn, "foo")
        a = motor.MotorGridIn(
            self.db.fs,
            _id=5,
            filename="my_file",
            contentType="text/html",
            chunkSize=1000,
            aliases=["foo"],
            metadata={"foo": 1, "bar": 2},
            bar=3,
            baz="hello",
        )

        self.assertEqual(5, a._id)
        self.assertEqual("my_file", a.filename)
        self.assertEqual("text/html", a.content_type)
        self.assertEqual(1000, a.chunk_size)
        self.assertEqual(["foo"], a.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, a.metadata)
        self.assertEqual(3, a.bar)
        self.assertEqual("hello", a.baz)
        self.assertRaises(AttributeError, getattr, a, "mike")

        b = motor.MotorGridIn(self.db.fs, content_type="text/html", chunk_size=1000, baz=100)

        self.assertEqual("text/html", b.content_type)
        self.assertEqual(1000, b.chunk_size)
        self.assertEqual(100, b.baz)

    @gen_test
    async def test_grid_out_default_opts(self):
        self.assertRaises(TypeError, motor.MotorGridOut, "foo")
        gout = motor.MotorGridOut(self.db.fs, 5)
        with self.assertRaises(NoFile):
            await gout.open()

        a = motor.MotorGridIn(self.db.fs)
        await a.close()

        b = await motor.MotorGridOut(self.db.fs, a._id).open()

        self.assertEqual(a._id, b._id)
        self.assertEqual(0, b.length)
        self.assertEqual(None, b.content_type)
        self.assertEqual(255 * 1024, b.chunk_size)
        self.assertTrue(isinstance(b.upload_date, datetime.datetime))
        self.assertEqual(None, b.aliases)
        self.assertEqual(None, b.metadata)

    @gen_test
    async def test_grid_out_custom_opts(self):
        one = motor.MotorGridIn(
            self.db.fs,
            _id=5,
            filename="my_file",
            contentType="text/html",
            chunkSize=1000,
            aliases=["foo"],
            metadata={"foo": 1, "bar": 2},
            bar=3,
            baz="hello",
        )

        await one.write(b"hello world")
        await one.close()

        two = await motor.MotorGridOut(self.db.fs, 5).open()

        self.assertEqual(5, two._id)
        self.assertEqual(11, two.length)
        self.assertEqual("text/html", two.content_type)
        self.assertEqual(1000, two.chunk_size)
        self.assertTrue(isinstance(two.upload_date, datetime.datetime))
        self.assertEqual(["foo"], two.aliases)
        self.assertEqual({"foo": 1, "bar": 2}, two.metadata)
        self.assertEqual(3, two.bar)

    @gen_test
    async def test_grid_out_file_document(self):
        one = motor.MotorGridIn(self.db.fs)
        await one.write(b"foo bar")
        await one.close()

        file_document = await self.db.fs.files.find_one()
        two = motor.MotorGridOut(self.db.fs, file_document=file_document)

        self.assertEqual(b"foo bar", (await two.read()))

        file_document = await self.db.fs.files.find_one()
        three = motor.MotorGridOut(self.db.fs, 5, file_document)
        self.assertEqual(b"foo bar", (await three.read()))

        gridout = motor.MotorGridOut(self.db.fs, file_document={})
        with self.assertRaises(NoFile):
            await gridout.open()

    @gen_test
    async def test_write_file_like(self):
        one = motor.MotorGridIn(self.db.fs)
        await one.write(b"hello world")
        await one.close()

        two = motor.MotorGridOut(self.db.fs, one._id)
        three = motor.MotorGridIn(self.db.fs)
        await three.write(two)
        await three.close()

        four = motor.MotorGridOut(self.db.fs, three._id)
        self.assertEqual(b"hello world", (await four.read()))

    @gen_test
    async def test_set_after_close(self):
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

        await f.close()

        self.assertEqual("foo", f._id)
        self.assertEqual("foo", f.bar)
        self.assertEqual(5, f.baz)
        self.assertTrue(f.uploadDate)

        self.assertRaises(AttributeError, setattr, f, "_id", 5)
        await f.set("bar", "a")
        await f.set("baz", "b")
        self.assertRaises(AttributeError, setattr, f, "upload_date", 5)

        g = await motor.MotorGridOut(self.db.fs, f._id).open()
        self.assertEqual("a", g.bar)
        self.assertEqual("b", g.baz)

    @gen_test
    async def test_stream_to_handler(self):
        fs = motor.MotorGridFSBucket(self.db)

        for content_length in (0, 1, 100, 100 * 1000):
            _id = await fs.upload_from_stream("filename", b"a" * content_length)
            gridout = await fs.open_download_stream(_id)
            handler = MockRequestHandler()
            await gridout.stream_to_handler(handler)
            self.assertEqual(content_length, handler.n_written)
            await fs.delete(_id)

    @gen_test
    async def test_exception_closed(self):
        contents = b"Imagine this is some important data..."
        with self.assertRaises(ConnectionError):
            async with motor.MotorGridIn(self.db.fs, _id="foo", bar="baz") as infile:
                infile.write(contents)
                raise ConnectionError("Test exception")

        self.assertTrue(infile.closed)


if __name__ == "__main__":
    unittest.main()
