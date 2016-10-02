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

    address       = ReadOnlyProperty()
    add_option    = MotorCursorChainingMethod()
    comment       = MotorCursorChainingMethod()
    conn_id       = ReadOnlyProperty()
    count         = AsyncRead()
    distinct      = AsyncRead()
    explain       = AsyncRead()
    hint          = MotorCursorChainingMethod()
    limit         = MotorCursorChainingMethod()
    max           = MotorCursorChainingMethod()
    max_scan      = MotorCursorChainingMethod()
    max_time_ms   = MotorCursorChainingMethod()
    min           = MotorCursorChainingMethod()
    remove_option = MotorCursorChainingMethod()
    skip          = MotorCursorChainingMethod()
    sort          = MotorCursorChainingMethod()
    where         = MotorCursorChainingMethod()

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
                file_document,
                _connect=False)

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
        :class:`tornado.web.RequestHandler`. This method calls `flush` on
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
the file is already closed, calling `set` will immediately update the file
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


class _MotorDelegateGridFS(gridfs.GridFS):

    # PyMongo's put() implementation uses requests, so rewrite for Motor.
    # w >= 1 necessary to avoid running 'filemd5' command before all data
    # is written, especially with sharding.
    #
    # Motor runs this on a thread.

    def put(self, data, **kwargs):
        """Put data into GridFS as a new file.

        Equivalent to doing:

        .. code-block:: python

            @gen.coroutine
            def f(data, **kwargs):
                try:
                    f = yield my_gridfs.new_file(**kwargs)
                    yield f.write(data)
                finally:
                    yield f.close()

        `data` can be either an instance of :class:`str` (:class:`bytes`
        in python 3) or a file-like object providing a :meth:`read` method.
        If an `encoding` keyword argument is passed, `data` can also be a
        :class:`unicode` (:class:`str` in python 3) instance, which will
        be encoded as `encoding` before being written. Any keyword arguments
        will be passed through to the created file - see
        :meth:`~MotorGridIn` for possible arguments.

        If the ``"_id"`` of the file is manually specified, it must
        not already exist in GridFS. Otherwise
        :class:`~gridfs.errors.FileExists` is raised.

        :Parameters:
          - `data`: data to be written as a file.
          - `callback`: Optional function taking parameters (_id, error)
          - `**kwargs` (optional): keyword arguments for file creation

        If no callback is provided, returns a Future that resolves to the
        ``"_id"`` of the created file. Otherwise, executes the callback
        with arguments (_id, error).

        Note that PyMongo allows unacknowledged ("w=0") puts to GridFS,
        but Motor does not.
        """
        collection = self._GridFS__collection
        if 0 == collection.write_concern.get('w'):
            raise pymongo.errors.ConfigurationError(
                "Motor does not allow unacknowledged put() to GridFS")

        grid_in = grid_file.GridIn(collection, **kwargs)

        try:
            grid_in.write(data)
        finally:
            grid_in.close()

        return grid_in._id


class AgnosticGridFS(object):
    __motor_class_name__ = 'MotorGridFS'
    __delegate_class__ = _MotorDelegateGridFS

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
            collection,
            _connect=False)

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
          - `spec` (optional): a SON object specifying elements which
            must be present for a document to be included in the
            result set
          - `skip` (optional): the number of files to omit (from
            the start of the result set) when returning the results
          - `limit` (optional): the maximum number of results to
            return
          - `timeout` (optional): if True (the default), any returned
            cursor is closed by the server after 10 minutes of
            inactivity. If set to False, the returned cursor will never
            time out on the server. Care should be taken to ensure that
            cursors with timeout turned off are properly closed.
          - `sort` (optional): a list of (key, direction) pairs
            specifying the sort order for this query. See
            :meth:`~pymongo.cursor.Cursor.sort` for details.
          - `max_scan` (optional): limit the number of file documents
            examined when performing the query
          - `read_preference` (optional): The read preference for
            this query.
          - `tag_sets` (optional): The tag sets for this query.
          - `secondary_acceptable_latency_ms` (optional): Any replica-set
            member whose ping time is within secondary_acceptable_latency_ms of
            the nearest member may accept reads. Default 15 milliseconds.
            **Ignored by mongos** and must be configured on the command line.
            See the localThreshold_ option for more information.
          - `compile_re` (optional): if ``False``, don't attempt to compile
            BSON regex objects into Python regexes. Return instances of
            :class:`~bson.regex.Regex` instead.

        Returns an instance of :class:`~motor.MotorGridOutCursor`
        corresponding to this query.

        .. versionadded:: 0.2
        .. mongodoc:: find
        .. _localThreshold: http://docs.mongodb.org/manual/reference/mongos/#cmdoption-mongos--localThreshold
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
