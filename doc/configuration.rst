Configuration
=============

TLS Protocol Version
''''''''''''''''''''

Industry best practices, and some regulations, require the use
of TLS 1.1 or newer. Though no application changes are required for
Motor to make use of the newest protocols, some operating systems or
versions may not provide an OpenSSL version new enough to support them.

Users of macOS older than 10.13 (High Sierra) will need to install Python
from `python.org`_, `homebrew`_, `macports`_, or another similar source.

Users of Linux or other non-macOS Unix can check their OpenSSL version like
this::

  $ openssl version

If the version number is less than 1.0.1 support for TLS 1.1 or newer is not
available. Contact your operating system vendor for a solution or upgrade to
a newer distribution.

You can check your Python interpreter by installing the `requests`_ module
and executing the following command::

  python -c "import requests; print(requests.get('https://www.howsmyssl.com/a/check', verify=False).json()['tls_version'])"

You should see "TLS 1.X" where X is >= 1.

You can read more about TLS versions and their security implications in this `cheat sheet`_.


.. _python.org: https://www.python.org/downloads/
.. _homebrew: https://brew.sh/
.. _macports: https://www.macports.org/
.. _requests: https://pypi.python.org/pypi/requests
.. _cheat sheet: https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html#only-support-strong-protocols

Thread Pool Size
''''''''''''''''

Motor uses the Python standard library's :class:`~concurrent.futures.ThreadPoolExecutor` to defer network
operations to threads. By default, the executor uses at most five threads per CPU core on your
system; to override the default set the environment variable ``MOTOR_MAX_WORKERS``.

Some additional threads are used for monitoring servers and background tasks, so the total
count of threads in your process will be greater.

Network Compression
'''''''''''''''''''

Like PyMongo, Motor supports network compression where network traffic between
the client and MongoDB server are compressed.
Keyword arguments to the Motor clients match those in MongoClient, documented
`here <https://pymongo.readthedocs.io/en/stable/examples/network_compression.html>`_.
By default no compression is used. If you wish to use wire compression,
you will have to install one of the optional dependencies.
Snappy requires `python-snappy <https://pypi.org/project/python-snappy>`_
and zstandard requires `zstandard <https://pypi.org/project/zstandard>`_::

  $ python3 -m pip install "motor[snappy, zstd]"
