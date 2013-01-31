Motor GridFS Classes
====================

.. currentmodule:: motor

Store blobs of data in `GridFS <http://www.mongodb.org/display/DOCS/GridFS>`_.

.. seealso:: :ref:`Differences between PyMongo's and Motor's GridFS APIs
  <gridfs-differences>`.

.. seealso:: :ref:`gridfs-handler`

.. autoclass:: MotorGridFS
  :members:


.. autoclass:: MotorGridIn
  :members:

  .. autoattribute:: _id
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


.. autoclass:: MotorGridOut
  :members:

  .. autoattribute:: _id
