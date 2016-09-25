# Copyright 2011-2015 MongoDB, Inc.
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

from __future__ import unicode_literals, absolute_import

"""GridFS implementation for Motor, an asynchronous driver for MongoDB."""

import gridfs
import pymongo
import pymongo.errors
from gridfs import grid_file

from motor.core import (AgnosticBaseCursor,
                        AgnosticCollection,
                        AgnosticDatabase)
from motor.metaprogramming import (AsyncCommand,
                                   AsyncRead,
                                   coroutine_annotation,
                                   create_class_with_framework,
                                   DelegateMethod,
                                   motor_coroutine,
                                   MotorCursorChainingMethod,
                                   ReadOnlyProperty)


class AgnosticGridOutCursor(AgnosticBaseCursor):
    __motor_class_name__ = 'MotorGridOutCursor'
    __delegate_class__ = gridfs.GridOutCursor

    add_option        = MotorCursorChainingMethod()
    address           = ReadOnlyProperty()
    comment           = MotorCursorChainingMethod()
    count             = AsyncRead()
    distinct          = AsyncRead()
    explain           = AsyncRead()
    hint              = MotorCursorChainingMethod()
    limit             = MotorCursorChainingMethod()
    max               = MotorCursorChainingMethod()
    max_await_time_ms = MotorCursorChainingMethod()
    max_scan          = MotorCursorChainingMethod()
    max_time_ms       = MotorCursorChainingMethod()
    min               = MotorCursorChainingMethod()
    remove_option     = MotorCursorChainingMethod()
    skip              = MotorCursorChainingMethod()
    sort              = MotorCursorChainingMethod()
    where             = MotorCursorChainingMethod()

    # PyMongo's GridOutCursor inherits __die from Cursor.
    _Cursor__die = AsyncCommand()

    def clone(self):
        """Get a clone of this cursor."""
        return self.__class__(self.delegate.clone(), self.collection)

    def next_object(self):
        """Get next GridOut object from cursor."""
        grid_out = super(self.__class__, self).next_object()
        if grid_out:
            grid_out_class = create_class_with_framework(
                AgnosticGridOut, self._framework, self.__module__)

            return grid_out_class(self.collection, delegate=grid_out)
        else:
            # Exhausted.
            return None

    def rewind(self):
        """Rewind this cursor to its unevaluated state."""
        self.delegate.rewind()
        self.started = False
        return self

    def _empty(self):
        return self.delegate._Cursor__empty

    def _query_flags(self):
        return self.delegate._Cursor__query_flags

    def _data(self):
        return self.delegate._Cursor__data

    def _clear_cursor_id(self):
        self.delegate._Cursor__id = 0

    def _close_exhaust_cursor(self):
        # Exhaust MotorGridOutCursors are prohibited.
        pass

    def _killed(self):
        return self.delegate._Cursor__killed

    @motor_coroutine
    def _close(self):
        yield self._framework.yieldable(self._Cursor__die())


class MotorGridOutProperty(ReadOnlyProperty):
    """Creates a readonly attribute on the wrapped PyMongo GridOut."""
    def create_attribute(self, cls, attr_name):
        def fget(obj):
            if not obj.delegate._file:
                raise pymongo.errors.InvalidOperation(
                    "You must call MotorGridOut.open() before accessing "
                    "the %s property" % attr_name)

            return getattr(obj.delegate, attr_name)

        doc = getattr(cls.__delegate_class__, attr_name).__doc__
        return property(fget=fget, doc=doc)


class AgnosticGridOut(object):
    """Class to read data out of GridFS.

    MotorGridOut supports the same attributes as PyMongo's
    :class:`~gridfs.grid_file.GridOut`, such as ``_id``, ``content_type``,
    etc.

    You don't need to instantiate this class directly - use the
    methods provided by :class:`~motor.MotorGridFS`. If it **is**
    instantiated directly, call :meth:`open`, :meth:`read`, or
    :meth:`readline` before accessing its attributes.
    """
    __motor_class_name__ = 'MotorGridOut'
    __delegate_class__ = gridfs.GridOut

    _ensure_file = AsyncCommand()
    aliases      = MotorGridOutProperty()
    chunk_size   = MotorGridOutProperty()
    close        = MotorGridOutProperty()
    content_type = MotorGridOutProperty()
    filename     = MotorGridOutProperty()
    length       = MotorGridOutProperty()
    md5          = MotorGridOutProperty()
    metadata     = MotorGridOutProperty()
    name         = MotorGridOutProperty()
    read         = AsyncRead()
    readchunk    = AsyncRead()
    readline     = AsyncRead()
    seek         = DelegateMethod()
    tell         = DelegateMethod()
    upload_date  = MotorGridOutProperty()

    def __init__(
        self,
        root_collection,
        file_id=None,
        file_document=None,
        delegate=None,
    ):
        collection_class = create_class_with_framework(
            AgnosticCollection, self._framework, self.__module__)

        if not isinstance(root_collection, collection_class):
            raise TypeError(
                "First argument to MotorGridOut must be "
                "MotorCollection, not %r" % root_collection)

        if delegate:
            self.delegate = delegate
        else:
            self.delegate = self.__delegate_class__(
                root_collection.delegate,
                file_id,
                file_document)

        self.io_loop = root_collection.get_io_loop()

    def __getattr__(self, item):
        if not self.delegate._file:
            raise pymongo.errors.InvalidOperation(
                "You must call MotorGridOut.open() before accessing "
                "the %s property" % item)

        return getattr(self.delegate, item)

    @coroutine_annotation
    def open(self, callback=None):
        """Retrieve this file's attributes from the server.

        Takes an optional callback, or returns a Future.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)

        .. versionchanged:: 0.2
           :class:`~motor.MotorGridOut` now opens itself on demand, calling
           ``open`` explicitly is rarely needed.
        """
        return self._framework.future_or_callback(self._ensure_file(),
                                                  callback,
                                                  self.get_io_loop(),
                                                  self)

    def get_io_loop(self):
        return self.io_loop

    @motor_coroutine
    def stream_to_handler(self, request_handler):
        """Write the contents of this file to a
        :class:`tornado.web.RequestHandler`. This method calls
        :meth:`~tornado.web.RequestHandler.flush` on
        the RequestHandler, so ensure all headers have already been set.
        For a more complete example see the implementation of
        :class:`~motor.web.GridFSHandler`.

        Takes an optional callback, or returns a Future.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)

        .. code-block:: python

            class FileHandler(tornado.web.RequestHandler):
                @tornado.web.asynchronous
                @gen.coroutine
                def get(self, filename):
                    db = self.settings['db']
                    fs = yield motor.MotorGridFS(db()).open()
                    try:
                        gridout = yield fs.get_last_version(filename)
                    except gridfs.NoFile:
                        raise tornado.web.HTTPError(404)

                    self.set_header("Content-Type", gridout.content_type)
                    self.set_header("Content-Length", gridout.length)
                    yield gridout.stream_to_handler(self)
                    self.finish()

        .. seealso:: Tornado `RequestHandler <http://tornadoweb.org/en/stable/web.html#request-handlers>`_
        """
        written = 0
        while written < self.length:
            # Reading chunk_size at a time minimizes buffering.
            f = self._framework.yieldable(self.read(self.chunk_size))
            yield f
            chunk = f.result()

            # write() simply appends the output to a list; flush() sends it
            # over the network and minimizes buffering in the handler.
            request_handler.write(chunk)
            request_handler.flush()
            written += len(chunk)


class AgnosticGridIn(object):
    __motor_class_name__ = 'MotorGridIn'
    __delegate_class__ = gridfs.GridIn

    __getattr__ = DelegateMethod()
    abort = AsyncCommand()
    closed = ReadOnlyProperty()
    close = AsyncCommand()
    write = AsyncCommand().unwrap('MotorGridOut')
    writelines = AsyncCommand().unwrap('MotorGridOut')
    _id = ReadOnlyProperty()
    md5 = ReadOnlyProperty()
    filename = ReadOnlyProperty()
    name = ReadOnlyProperty()
    content_type = ReadOnlyProperty()
    length = ReadOnlyProperty()
    chunk_size = ReadOnlyProperty()
    upload_date = ReadOnlyProperty()
    set = AsyncCommand(attr_name='__setattr__', doc="""
Set an arbitrary metadata attribute on the file. Stores value on the server
as a key-value pair within the file document once the file is closed. If
the file is already closed, calling :meth:`set` will immediately update the file
document on the server.

Metadata set on the file appears as attributes on a
:class:`~motor.MotorGridOut` object created from the file.

:Parameters:
  - `name`: Name of the attribute, will be stored as a key in the file
    document on the server
  - `value`: Value of the attribute
  - `callback`: Optional callback to execute once attribute is set.
""")

    def __init__(self, root_collection, delegate=None, **kwargs):
        """
        Class to write data to GridFS. Application developers should not
        generally need to instantiate this class - see
        :meth:`~motor.MotorGridFS.new_file`.

        Any of the file level options specified in the `GridFS Spec
        <http://dochub.mongodb.org/core/gridfs>`_ may be passed as
        keyword arguments. Any additional keyword arguments will be
        set as additional fields on the file document. Valid keyword
        arguments include:

          - ``"_id"``: unique ID for this file (default:
            :class:`~bson.objectid.ObjectId`) - this ``"_id"`` must
            not have already been used for another file

          - ``"filename"``: human name for the file

          - ``"contentType"`` or ``"content_type"``: valid mime-type
            for the file

          - ``"chunkSize"`` or ``"chunk_size"``: size of each of the
            chunks, in bytes (default: 256 kb)

          - ``"encoding"``: encoding used for this file. In Python 2,
            any :class:`unicode` that is written to the file will be
            converted to a :class:`str`. In Python 3, any :class:`str`
            that is written to the file will be converted to
            :class:`bytes`.

        :Parameters:
          - `root_collection`: A :class:`~motor.MotorCollection`, the root
             collection to write to
          - `**kwargs` (optional): file level options (see above)

        .. versionchanged:: 0.2
           ``open`` method removed, no longer needed.
        """
        collection_class = create_class_with_framework(
            AgnosticCollection, self._framework, self.__module__)

        if not isinstance(root_collection, collection_class):
            raise TypeError(
                "First argument to MotorGridIn must be "
                "MotorCollection, not %r" % root_collection)

        self.io_loop = root_collection.get_io_loop()
        if delegate:
            # Short cut.
            self.delegate = delegate
        else:
            self.delegate = self.__delegate_class__(
                root_collection.delegate,
                **kwargs)

    def get_io_loop(self):
        return self.io_loop


class AgnosticGridFS(object):
    __motor_class_name__ = 'MotorGridFS'
    __delegate_class__ = gridfs.GridFS

    find_one = AsyncRead().wrap(grid_file.GridOut)
    new_file = AsyncRead().wrap(grid_file.GridIn)
    get = AsyncRead().wrap(grid_file.GridOut)
    get_version = AsyncRead().wrap(grid_file.GridOut)
    get_last_version = AsyncRead().wrap(grid_file.GridOut)
    list = AsyncRead()
    exists = AsyncRead()
    delete = AsyncCommand()
    put = AsyncCommand()

    def __init__(self, database, collection="fs"):
        """An instance of GridFS on top of a single Database.

        :Parameters:
          - `database`: a :class:`~motor.MotorDatabase`
          - `collection` (optional): A string, name of root collection to use,
            such as "fs" or "my_files"

        .. mongodoc:: gridfs

        .. versionchanged:: 0.2
           ``open`` method removed; no longer needed.
        """
        db_class = create_class_with_framework(
            AgnosticDatabase, self._framework, self.__module__)

        if not isinstance(database, db_class):
            raise TypeError("First argument to MotorGridFS must be "
                            "MotorDatabase, not %r" % database)

        self.io_loop = database.get_io_loop()
        self.collection = database[collection]
        self.delegate = self.__delegate_class__(
            database.delegate,
            collection)

    def get_io_loop(self):
        return self.io_loop

    def find(self, *args, **kwargs):
        """Query GridFS for files.

        Returns a cursor that iterates across files matching
        arbitrary queries on the files collection. Can be combined
        with other modifiers for additional control. For example::

          cursor = fs.find({"filename": "lisa.txt"}, timeout=False)
          while (yield cursor.fetch_next):
              grid_out = cursor.next_object()
              data = yield grid_out.read()

        This iterates through all versions of "lisa.txt" stored in GridFS.
        Note that setting timeout to False may be important to prevent the
        cursor from timing out during long multi-file processing work.

        As another example, the call::

          most_recent_three = fs.find().sort("uploadDate", -1).limit(3)

        would return a cursor to the three most recently uploaded files
        in GridFS.

        :meth:`~motor.MotorGridFS.find` follows a similar
        interface to :meth:`~motor.MotorCollection.find`
        in :class:`~motor.MotorCollection`.

        :Parameters:
          - `filter` (optional): a SON object specifying elements which
            must be present for a document to be included in the
            result set
          - `skip` (optional): the number of files to omit (from
            the start of the result set) when returning the results
          - `limit` (optional): the maximum number of results to
            return
          - `no_cursor_timeout` (optional): if False (the default), any
            returned cursor is closed by the server after 10 minutes of
            inactivity. If set to True, the returned cursor will never
            time out on the server. Care should be taken to ensure that
            cursors with no_cursor_timeout turned on are properly closed.
          - `sort` (optional): a list of (key, direction) pairs
            specifying the sort order for this query. See
            :meth:`~pymongo.cursor.Cursor.sort` for details.

        Raises :class:`TypeError` if any of the arguments are of
        improper type. Returns an instance of
        :class:`~gridfs.grid_file.GridOutCursor`
        corresponding to this query.

        .. versionchanged:: 1.0
           Removed the read_preference, tag_sets, and
           secondary_acceptable_latency_ms options.

        .. versionadded:: 0.2

        .. mongodoc:: find
        """
        cursor = self.delegate.find(*args, **kwargs)
        grid_out_cursor = create_class_with_framework(
            AgnosticGridOutCursor, self._framework, self.__module__)

        return grid_out_cursor(cursor, self.collection)

    def wrap(self, obj):
        if obj.__class__ is grid_file.GridIn:
            grid_in_class = create_class_with_framework(
                AgnosticGridIn, self._framework, self.__module__)

            return grid_in_class(
                root_collection=self.collection,
                delegate=obj)

        elif obj.__class__ is grid_file.GridOut:
            grid_out_class = create_class_with_framework(
                AgnosticGridOut, self._framework, self.__module__)

            return grid_out_class(
                root_collection=self.collection,
                delegate=obj)

        elif obj.__class__ is gridfs.GridOutCursor:
            grid_out_class = create_class_with_framework(
                AgnosticGridOutCursor, self._framework, self.__module__)

            return grid_out_class(
                cursor=obj,
                collection=self.collection)
