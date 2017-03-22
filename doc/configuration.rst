Configuration
=============

Motor uses the Python standard library's :class:`~concurrent.futures.ThreadPoolExecutor` to defer network
operations to threads. By default, the executor uses at most five threads per CPU core on your
system; to override the default set the environment variable ``MOTOR_MAX_WORKERS``.

Some additional threads are used for monitoring servers and background tasks, so the total
count of threads in your process will be greater.
