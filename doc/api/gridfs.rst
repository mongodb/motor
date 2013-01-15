Motor GridFS Classes
====================

.. currentmodule:: motor

Store blobs of data in `GridFS <http://www.mongodb.org/display/DOCS/GridFS>`_.

.. seealso:: :ref:`gridfs-handler`

.. TODO: doc all the differences, link from differences.rst

.. autoclass:: MotorGridFS

  .. automethod:: open
  .. automotormethod:: new_file
  .. automotormethod:: get
  .. automotormethod:: get_version
  .. automotormethod:: get_last_version
  .. automotormethod:: list
  .. automotormethod:: exists
  .. automotormethod:: put
  .. automotormethod:: delete


.. autoclass:: MotorGridIn

  .. automotorattribute:: _id
  .. automotorattribute:: filename
  .. automotorattribute:: name
  .. automotorattribute:: content_type
  .. automotorattribute:: length
  .. automotorattribute:: chunk_size
  .. automotorattribute:: upload_date
  .. automotorattribute:: md5
  .. automotorattribute:: closed
  .. automethod:: open
  .. automotormethod:: write
  .. automotormethod:: writelines
  .. method:: set(name, value, callback=None)

    Set an arbitrary metadata attribute on the file. Stores value on the server
    as a key-value pair within the file document once the file is closed. If
    the file is already closed, calling `set` will immediately update the file
    document on the server.

    Metadata set on the file appears as attributes on a :class:`~MotorGridOut`
    object created from the file.

    :Parameters:
      - `name`: Name of the attribute, will be stored as a key in the file
        document on the server
      - `value`: Value of the attribute
      - `callback`: Optional callback to execute once attribute is set.

  .. automotormethod:: close


.. autoclass:: MotorGridOut

  .. automotorattribute:: _id
  .. automotorattribute:: filename
  .. automotorattribute:: name
  .. automotorattribute:: content_type
  .. automotorattribute:: length
  .. automotorattribute:: chunk_size
  .. automotorattribute:: upload_date
  .. automotorattribute:: md5
  .. automethod:: open
  .. automotormethod:: tell
  .. automotormethod:: seek
  .. automotormethod:: read
  .. automotormethod:: readline
  .. automethod:: stream_to_handler
