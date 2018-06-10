asyncio GridFS Classes
======================

.. currentmodule:: motor.motor_asyncio

Store blobs of data in `GridFS <http://dochub.mongodb.org/core/gridfs>`_.

.. seealso:: :ref:`Differences between PyMongo's and Motor's GridFS APIs
  <gridfs-differences>`.


.. class:: AsyncIOMotorGridFSBucket

  Create a new instance of :class:`AsyncIOMotorGridFSBucket`.

  Raises :exc:`TypeError` if `database` is not an instance of
  :class:`AsyncIOMotorDatabase`.

  Raises :exc:`~pymongo.errors.ConfigurationError` if `write_concern`
  is not acknowledged.

  :Parameters:
    - `database`: database to use.
    - `bucket_name` (optional): The name of the bucket. Defaults to 'fs'.
    - `chunk_size_bytes` (optional): The chunk size in bytes. Defaults
      to 255KB.
    - `write_concern` (optional): The
      :class:`~pymongo.write_concern.WriteConcern` to use. If ``None``
      (the default) db.write_concern is used.
    - `read_preference` (optional): The read preference to use. If
      ``None`` (the default) db.read_preference is used.

  .. mongodoc:: gridfs

  .. coroutinemethod:: delete(self, file_id)

      Delete a file's metadata and data chunks from a GridFS bucket::

          async def delete():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # Get _id of file to delete
              file_id = await fs.upload_from_stream("test_file",
                                                    b"data I want to store!")
              await fs.delete(file_id)

      Raises :exc:`~gridfs.errors.NoFile` if no file with file_id exists.

      :Parameters:
        - `file_id`: The _id of the file to be deleted.

  .. coroutinemethod:: download_to_stream(self, file_id, destination)

      Downloads the contents of the stored file specified by file_id and
      writes the contents to `destination`::

          async def download():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # Get _id of file to read
              file_id = await fs.upload_from_stream("test_file",
                                                    b"data I want to store!")
              # Get file to write to
              file = open('myfile','wb+')
              await fs.download_to_stream(file_id, file)
              file.seek(0)
              contents = file.read()

      Raises :exc:`~gridfs.errors.NoFile` if no file with file_id exists.

      :Parameters:
        - `file_id`: The _id of the file to be downloaded.
        - `destination`: a file-like object implementing :meth:`write`.

  .. coroutinemethod:: download_to_stream_by_name(self, filename, destination, revision=-1)

      Write the contents of `filename` (with optional `revision`) to
      `destination`.

      For example::

          async def download_by_name():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # Get file to write to
              file = open('myfile','wb')
              await fs.download_to_stream_by_name("test_file", file)

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.

      Raises :exc:`~ValueError` if `filename` is not a string.

      :Parameters:
        - `filename`: The name of the file to read from.
        - `destination`: A file-like object that implements :meth:`write`.
        - `revision` (optional): Which revision (documents with the same
          filename and different uploadDate) of the file to retrieve.
          Defaults to -1 (the most recent revision).

      :Note: Revision numbers are defined as follows:

        - 0 = the original stored file
        - 1 = the first revision
        - 2 = the second revision
        - etc...
        - -2 = the second most recent revision
        - -1 = the most recent revision

  .. method:: find(self, *args, **kwargs)

      Find and return the files collection documents that match ``filter``.

      Returns a cursor that iterates across files matching
      arbitrary queries on the files collection. Can be combined
      with other modifiers for additional control.

      For example::

          async def find():
              cursor = fs.find({"filename": "lisa.txt"},
                               no_cursor_timeout=True)

              async for grid_data in cursor:
                  data = grid_data.read()

      iterates through all versions of "lisa.txt" stored in GridFS.
      Setting no_cursor_timeout may be important to
      prevent the cursor from timing out during long multi-file processing
      work.

      As another example, the call::

        most_recent_three = fs.find().sort("uploadDate", -1).limit(3)

      returns a cursor to the three most recently uploaded files in GridFS.

      Follows a similar interface to :meth:`~AsyncIOMotorCollection.find`
      in :class:`AsyncIOMotorCollection`.

      :Parameters:
        - `filter`: Search query.
        - `batch_size` (optional): The number of documents to return per
          batch.
        - `limit` (optional): The maximum number of documents to return.
        - `no_cursor_timeout` (optional): The server normally times out idle
          cursors after an inactivity period (10 minutes) to prevent excess
          memory use. Set this option to True prevent that.
        - `skip` (optional): The number of documents to skip before
          returning.
        - `sort` (optional): The order by which to sort results. Defaults to
          None.

  .. coroutinemethod:: open_download_stream(self, file_id)

      Opens a stream to read the contents of the stored file specified by file_id::

          async def download_stream():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # get _id of file to read.
              file_id = await fs.upload_from_stream("test_file",
                                                    b"data I want to store!")
              grid_out = await fs.open_download_stream(file_id)
              contents = await grid_out.read()

      Raises :exc:`~gridfs.errors.NoFile` if no file with file_id exists.

      :Parameters:
        - `file_id`: The _id of the file to be downloaded.

      Returns a :class:`AsyncIOMotorGridOut`.

  .. coroutinemethod:: open_download_stream_by_name(self, filename, revision=-1)

      Opens a stream to read the contents of `filename` and optional `revision`::

          async def download_by_name():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # get _id of file to read.
              file_id = await fs.upload_from_stream("test_file",
                                                    b"data I want to store!")
              grid_out = await fs.open_download_stream_by_name(file_id)
              contents = await grid_out.read()

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.

      Raises :exc:`~ValueError` filename is not a string.

      :Parameters:
        - `filename`: The name of the file to read from.
        - `revision` (optional): Which revision (documents with the same
          filename and different uploadDate) of the file to retrieve.
          Defaults to -1 (the most recent revision).

      Returns a :class:`AsyncIOMotorGridOut`.

      :Note: Revision numbers are defined as follows:

        - 0 = the original stored file
        - 1 = the first revision
        - 2 = the second revision
        - etc...
        - -2 = the second most recent revision
        - -1 = the most recent revision

  .. method:: open_upload_stream(self, filename, chunk_size_bytes=None, metadata=None)

      Opens a stream for writing.

      Specify the filename, and add any additional information in the metadata
      field of the file document or modify the chunk size::

          async def upload():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              grid_in, file_id = fs.open_upload_stream(
                  "test_file", chunk_size_bytes=4,
                  metadata={"contentType": "text/plain"})

              await grid_in.write(b"data I want to store!")
              await grid_in.close()  # uploaded on close

      Returns an instance of :class:`AsyncIOMotorGridIn`.

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.
      Raises :exc:`~ValueError` if `filename` is not a string.

      In a Python 3.5 native coroutine, the "async with" statement calls
      :meth:`~AsyncIOMotorGridIn.close` automatically::

          async def upload():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              async with await fs.new_file() as gridin:
                  await gridin.write(b'First part\n')
                  await gridin.write(b'Second part')

              # gridin is now closed automatically.

      :Parameters:
        - `filename`: The name of the file to upload.
        - `chunk_size_bytes` (options): The number of bytes per chunk of this
          file. Defaults to the chunk_size_bytes in :class:`AsyncIOMotorGridFSBucket`.
        - `metadata` (optional): User data for the 'metadata' field of the
          files collection document. If not provided the metadata field will
          be omitted from the files collection document.

  .. method:: open_upload_stream_with_id(self, file_id, filename, chunk_size_bytes=None, metadata=None)

      Opens a stream for writing.

      Specify the filed_id and filename, and add any additional information in
      the metadata field of the file document, or modify the chunk size::

          async def upload():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              grid_in, file_id = fs.open_upload_stream_with_id(
                  ObjectId(),
                  "test_file",
                  chunk_size_bytes=4,
                  metadata={"contentType": "text/plain"})

              await grid_in.write(b"data I want to store!")
              await grid_in.close()  # uploaded on close

      Returns an instance of :class:`AsyncIOMotorGridIn`.

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.
      Raises :exc:`~ValueError` if `filename` is not a string.

      :Parameters:
        - `file_id`: The id to use for this file. The id must not have
          already been used for another file.
        - `filename`: The name of the file to upload.
        - `chunk_size_bytes` (options): The number of bytes per chunk of this
          file. Defaults to the chunk_size_bytes in :class:`AsyncIOMotorGridFSBucket`.
        - `metadata` (optional): User data for the 'metadata' field of the
          files collection document. If not provided the metadata field will
          be omitted from the files collection document.

  .. coroutinemethod:: rename(self, file_id, new_filename)

      Renames the stored file with the specified file_id.

      For example::


          async def rename():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              # get _id of file to read.
              file_id = await fs.upload_from_stream("test_file",
                                                    b"data I want to store!")

              await fs.rename(file_id, "new_test_name")

      Raises :exc:`~gridfs.errors.NoFile` if no file with file_id exists.

      :Parameters:
        - `file_id`: The _id of the file to be renamed.
        - `new_filename`: The new name of the file.

  .. coroutinemethod:: upload_from_stream(self, filename, source, chunk_size_bytes=None, metadata=None)

      Uploads a user file to a GridFS bucket.

      Reads the contents of the user file from `source` and uploads
      it to the file `filename`. Source can be a string or file-like object.
      For example::

          async def upload_from_stream():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              file_id = await fs.upload_from_stream(
                  "test_file",
                  b"data I want to store!",
                  chunk_size_bytes=4,
                  metadata={"contentType": "text/plain"})

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.
      Raises :exc:`~ValueError` if `filename` is not a string.

      :Parameters:
        - `filename`: The name of the file to upload.
        - `source`: The source stream of the content to be uploaded. Must be
          a file-like object that implements :meth:`read` or a string.
        - `chunk_size_bytes` (options): The number of bytes per chunk of this
          file. Defaults to the chunk_size_bytes of :class:`AsyncIOMotorGridFSBucket`.
        - `metadata` (optional): User data for the 'metadata' field of the
          files collection document. If not provided the metadata field will
          be omitted from the files collection document.

      Returns the _id of the uploaded file.

  .. coroutinemethod:: upload_from_stream_with_id(self, file_id, filename, source, chunk_size_bytes=None, metadata=None)

      Uploads a user file to a GridFS bucket with a custom file id.

      Reads the contents of the user file from `source` and uploads
      it to the file `filename`. Source can be a string or file-like object.
      For example::

          async def upload_from_stream_with_id():
              my_db = AsyncIOMotorClient().test
              fs = AsyncIOMotorGridFSBucket(my_db)
              file_id = await fs.upload_from_stream_with_id(
                  ObjectId(),
                  "test_file",
                  b"data I want to store!",
                  chunk_size_bytes=4,
                  metadata={"contentType": "text/plain"})

      Raises :exc:`~gridfs.errors.NoFile` if no such version of
      that file exists.
      Raises :exc:`~ValueError` if `filename` is not a string.

      :Parameters:
        - `file_id`: The id to use for this file. The id must not have
          already been used for another file.
        - `filename`: The name of the file to upload.
        - `source`: The source stream of the content to be uploaded. Must be
          a file-like object that implements :meth:`read` or a string.
        - `chunk_size_bytes` (options): The number of bytes per chunk of this
          file. Defaults to the chunk_size_bytes of :class:`AsyncIOMotorGridFSBucket`.
        - `metadata` (optional): User data for the 'metadata' field of the
          files collection document. If not provided the metadata field will
          be omitted from the files collection document.

.. autoclass:: AsyncIOMotorGridIn
  :members:

.. autoclass:: AsyncIOMotorGridOut
  :members:

.. autoclass:: AsyncIOMotorGridOutCursor
  :members:
