# Copyright 2011-2012 10gen, Inc.
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

"""Utilities for using Motor with Tornado web applications."""

import datetime
import email.utils
import mimetypes
import time

import tornado.web
from tornado import gen

import gridfs
import motor


# TODO: this class is not a drop-in replacement for StaticFileHandler.
#   StaticFileHandler provides class method make_static_url, which appends
#   an MD5 of the static file's contents. Templates thus can do
#   {{ static_url('image.png') }} and get "/static/image.png?v=1234abcdef",
#   which is cached forever. Problem is, it calculates the MD5 synchronously.
#   Two options: keep a synchronous GridFS available to get each grid file's
#   MD5 synchronously for every static_url call, or find some other idiom.


class GridFSHandler(tornado.web.RequestHandler):
    """A handler that can serve content from `GridFS`_, very similar to
    `tornado.web.StaticFileHandler`.

    .. code-block:: python

        db = motor.MotorClient().open_sync().my_database
        application = web.Application([
            (r"/static/(.*)", web.GridFSHandler, {"database": db}),
        ])

    By default, requests' If-Modified-Since headers are honored, but no
    specific cache-control timeout is sent to clients. Thus each request for
    a GridFS file requires a quick check of the file's ``uploadDate`` in
    MongoDB. Override :meth:`get_cache_time` in a subclass to customize this.

    .. seealso:: MongoDB and `GridFS
       <http://docs.mongodb.org/manual/applications/gridfs/>`_

    .. seealso:: `StaticFileHandler
       <http://www.tornadoweb.org/documentation/web.html#tornado.web.StaticFileHandler>`_
    """
    def initialize(self, database, root_collection='fs'):
        self.database = database
        self.root_collection = root_collection

    def get_gridfs_file(self, fs, path, callback):
        """Overridable method to choose a GridFS file to serve at a URL.

        By default, if a URL pattern like ``"/static/(.*)"`` is mapped to this
        `GridFSHandler`, then the trailing portion of the URL is used as the
        filename, so a request for "/static/image.png" results in a call
        to `get_gridfs_file` with "image.png" as the ``path`` argument. To
        customize the mapping of path to GridFS file, override `get_gridfs_file`
        and pass an open :class:`~motor.MotorGridOut` to ``callback``.

        :Parameters:
          - `fs`: An open :class:`~motor.MotorGridFS` object
          - `path`: A string, the trailing portion of the URL pattern being
            served
          - `callback`: A function taking arguments (gridout, error)
        """
        fs.get_last_version(path, callback=callback)

    @tornado.web.asynchronous
    @gen.engine
    def get(self, path, include_body=True):
        fs = yield motor.Op(
            motor.MotorGridFS(self.database, self.root_collection).open)

        try:
            gridout = yield motor.Op(self.get_gridfs_file, fs, path)
        except gridfs.NoFile:
            raise tornado.web.HTTPError(404)

        # If-Modified-Since header is only good to the second.
        modified = gridout.upload_date.replace(microsecond=0)
        self.set_header("Last-Modified", modified)

        # MD5 is calculated on the MongoDB server when GridFS file is created
        self.set_header("Etag", '"%s"' % gridout.md5)

        mime_type = gridout.content_type

        # If content type is not defined, try to check it with mimetypes
        if mime_type is None:
            mime_type, encoding = mimetypes.guess_type(path)

        # Starting from here, largely a copy of StaticFileHandler
        if mime_type:
            self.set_header("Content-Type", mime_type)

        cache_time = self.get_cache_time(path, modified, mime_type)

        if cache_time > 0:
            self.set_header("Expires", datetime.datetime.utcnow() +
                                       datetime.timedelta(seconds=cache_time))
            self.set_header("Cache-Control", "max-age=" + str(cache_time))
        else:
            self.set_header("Cache-Control", "public")

        self.set_extra_headers(path, gridout)

        # Check the If-Modified-Since, and don't send the result if the
        # content has not been modified
        ims_value = self.request.headers.get("If-Modified-Since")
        if ims_value is not None:
            date_tuple = email.utils.parsedate(ims_value)
            if_since = datetime.datetime.fromtimestamp(time.mktime(date_tuple))
            if if_since >= modified:
                self.set_status(304)
                self.finish()
                raise StopIteration

        # Same for Etag
        etag = self.request.headers.get("If-None-Match")
        if etag is not None and etag.strip('"') == gridout.md5:
            self.set_status(304)
            self.finish()
            raise StopIteration

        self.set_header("Content-Length", gridout.length)
        if include_body:
            yield motor.Op(gridout.stream_to_handler, self)

        self.finish()

    def head(self, path):
        self.get(path, include_body=False)

    def get_cache_time(self, path, modified, mime_type):
        """Override to customize cache control behavior.

        Return a positive number of seconds to trigger aggressive caching or 0
        to mark resource as cacheable, only. 0 is the default.
        """
        return 0

    def set_extra_headers(self, path, gridout):
        """For subclass to add extra headers to the response"""
        pass
