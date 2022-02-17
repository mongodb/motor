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

"""Test utilities for using Motor with Tornado web applications."""

import datetime
import email
import re
import test
import time
import unittest
from test.test_environment import CA_PEM, CLIENT_PEM, env

import gridfs
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

import motor
import motor.web
from motor.motor_gridfs import _hash_gridout


# We're using Tornado's AsyncHTTPTestCase instead of our own MotorTestCase for
# the convenience of self.fetch().
class GridFSHandlerTestBase(AsyncHTTPTestCase):
    def setUp(self):
        super().setUp()

        self.fs = gridfs.GridFS(test.env.sync_cx.motor_test)

        # Make a 500k file in GridFS with filename 'foo'
        self.contents = b"Jesse" * 100 * 1024

        # Record when we created the file, to check the Last-Modified header
        self.put_start = datetime.datetime.utcnow().replace(microsecond=0)
        file_id = "id"
        self.file_id = file_id
        self.fs.delete(self.file_id)
        self.fs.put(self.contents, _id=file_id, filename="foo", content_type="my type")

        item = self.fs.get(file_id)
        self.contents_hash = _hash_gridout(item)
        self.put_end = datetime.datetime.utcnow().replace(microsecond=0)
        self.assertTrue(self.fs.get_last_version("foo"))

    def motor_db(self, **kwargs):
        if env.mongod_started_with_ssl:
            kwargs.setdefault("tlsCAFile", CA_PEM)
            kwargs.setdefault("tlsCertificateKeyFile", CLIENT_PEM)

        kwargs.setdefault("tls", env.mongod_started_with_ssl)

        client = motor.MotorClient(test.env.uri, io_loop=self.io_loop, **kwargs)

        return client.motor_test

    def tearDown(self):
        self.fs.delete(self.file_id)
        super().tearDown()

    def get_app(self):
        return Application([("/(.+)", motor.web.GridFSHandler, {"database": self.motor_db()})])

    def stop(self, *args, **kwargs):
        # A stop() method more permissive about the number of its positional
        # arguments than AsyncHTTPTestCase.stop
        if len(args) == 1:
            AsyncHTTPTestCase.stop(self, args[0], **kwargs)
        else:
            AsyncHTTPTestCase.stop(self, args, **kwargs)

    def parse_date(self, d):
        date_tuple = email.utils.parsedate(d)
        return datetime.datetime.fromtimestamp(time.mktime(date_tuple))

    def last_mod(self, response):
        """Parse the 'Last-Modified' header from an HTTP response into a
        datetime.
        """
        return self.parse_date(response.headers["Last-Modified"])

    def expires(self, response):
        return self.parse_date(response.headers["Expires"])


class GridFSHandlerTest(GridFSHandlerTestBase):
    def test_basic(self):
        # First request
        response = self.fetch("/foo")

        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)
        self.assertEqual(len(self.contents), int(response.headers["Content-Length"]))
        self.assertEqual("my type", response.headers["Content-Type"])
        self.assertEqual("public", response.headers["Cache-Control"])
        self.assertTrue("Expires" not in response.headers)

        etag = response.headers["Etag"]
        last_mod_dt = self.last_mod(response)
        self.assertEqual(self.contents_hash, etag.strip('"'))
        self.assertTrue(self.put_start <= last_mod_dt <= self.put_end)

        # Now check we get 304 NOT MODIFIED responses as appropriate
        for ims_value in (last_mod_dt, last_mod_dt + datetime.timedelta(seconds=1)):
            response = self.fetch("/foo", if_modified_since=ims_value)
            self.assertEqual(304, response.code)
            self.assertEqual(b"", response.body)

        # If-Modified-Since in the past, get whole response back
        response = self.fetch("/foo", if_modified_since=last_mod_dt - datetime.timedelta(seconds=1))
        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)

        # Matching Etag
        response = self.fetch("/foo", headers={"If-None-Match": etag})
        self.assertEqual(304, response.code)
        self.assertEqual(b"", response.body)

        # Mismatched Etag
        response = self.fetch("/foo", headers={"If-None-Match": etag + "a"})
        self.assertEqual(200, response.code)
        self.assertEqual(self.contents, response.body)

    def test_404(self):
        response = self.fetch("/bar")
        self.assertEqual(404, response.code)

    def test_head(self):
        response = self.fetch("/foo", method="HEAD")

        # Get Etag and parse Last-Modified into a datetime
        etag = response.headers["Etag"]
        last_mod_dt = self.last_mod(response)

        # Test the result
        self.assertEqual(200, response.code)
        self.assertEqual(b"", response.body)  # Empty body for HEAD request
        self.assertEqual(len(self.contents), int(response.headers["Content-Length"]))
        self.assertEqual("my type", response.headers["Content-Type"])
        self.assertEqual(self.contents_hash, etag.strip('"'))
        self.assertTrue(self.put_start <= last_mod_dt <= self.put_end)
        self.assertEqual("public", response.headers["Cache-Control"])

    def test_content_type(self):
        # Check that GridFSHandler uses file extension to guess Content-Type
        # if not provided
        for filename, expected_type in [
            ("foo.jpg", "jpeg"),
            ("foo.png", "png"),
            ("ht.html", "html"),
        ]:
            # 'fs' is PyMongo's blocking GridFS
            self.fs.put(b"", filename=filename)
            for method in "GET", "HEAD":
                response = self.fetch("/" + filename, method=method)
                self.assertEqual(200, response.code)
                # mimetypes are platform-defined, be fuzzy
                self.assertIn(expected_type, response.headers["Content-Type"].lower())


class TZAwareGridFSHandlerTest(GridFSHandlerTestBase):
    def motor_db(self):
        return super().motor_db(tz_aware=True)

    def test_tz_aware(self):
        now = datetime.datetime.utcnow()
        ago = now - datetime.timedelta(minutes=10)
        hence = now + datetime.timedelta(minutes=10)

        response = self.fetch("/foo", if_modified_since=ago)
        self.assertEqual(200, response.code)

        response = self.fetch("/foo", if_modified_since=hence)
        self.assertEqual(304, response.code)


class CustomGridFSHandlerTest(GridFSHandlerTestBase):
    def get_app(self):
        class CustomGridFSHandler(motor.web.GridFSHandler):
            def get_gridfs_file(self, bucket, filename, request):
                # Test overriding the get_gridfs_file() method, path is
                # interpreted as file_id instead of filename.
                return bucket.open_download_stream(file_id=filename)

            def get_cache_time(self, path, modified, mime_type):
                return 10

            def set_extra_headers(self, path, gridout):
                self.set_header("quux", "fizzledy")

        return Application([("/(.+)", CustomGridFSHandler, {"database": self.motor_db()})])

    def test_get_gridfs_file(self):
        # We overrode get_gridfs_file so we expect getting by filename *not* to
        # work now; we'll get a 404. We have to get by file_id now.
        response = self.fetch("/foo")
        self.assertEqual(404, response.code)

        response = self.fetch("/" + str(self.file_id))
        self.assertEqual(200, response.code)

        self.assertEqual(self.contents, response.body)
        cache_control = response.headers["Cache-Control"]
        self.assertTrue(re.match(r"max-age=\d+", cache_control))
        self.assertEqual(10, int(cache_control.split("=")[1]))
        expires = self.expires(response)

        # It should expire about 10 seconds from now
        self.assertTrue(
            datetime.timedelta(seconds=8)
            < expires - datetime.datetime.utcnow()
            < datetime.timedelta(seconds=12)
        )

        self.assertEqual("fizzledy", response.headers["quux"])


if __name__ == "__main__":
    unittest.main()
