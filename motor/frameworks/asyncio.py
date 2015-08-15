# Copyright 2014 MongoDB, Inc.
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

# TODO: link to framework spec in dev guide.
"""asyncio compatibility layer for Motor, an asynchronous MongoDB driver."""

import asyncio
import asyncio.tasks
import functools
import socket
import ssl

import greenlet


def get_event_loop():
    return asyncio.get_event_loop()


def is_event_loop(loop):
    return isinstance(loop, asyncio.AbstractEventLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError(
            "io_loop must be instance of asyncio-compatible event loop,"
            "not %r" % loop)


def return_value(value):
    # In Python 3.3, StopIteration can accept a value.
    raise StopIteration(value)


def get_future(loop):
    return asyncio.Future(loop=loop)


def is_future(f):
    return isinstance(f, asyncio.Future)


def call_soon(loop, callback, *args, **kwargs):
    if kwargs:
        loop.call_soon(functools.partial(callback, *args, **kwargs))
    else:
        loop.call_soon(callback, *args)


def call_soon_threadsafe(loop, callback):
    loop.call_soon_threadsafe(callback)


def call_later(loop, delay, callback, *args, **kwargs):
    if kwargs:
        return loop.call_later(delay,
                               functools.partial(callback, *args, **kwargs))
    else:
        return loop.call_later(delay, callback, *args)


def call_later_cancel(loop, handle):
    handle.cancel()


def create_task(loop, coro, *args, **kwargs):
    asyncio.tasks.Task(coro(*args, **kwargs), loop=loop)


def get_resolver(loop):
    # asyncio's resolver just calls getaddrinfo in a thread. It's not yet
    # configurable, see https://code.google.com/p/tulip/issues/detail?id=160
    return None


def close_resolver(resolver):
    pass


coroutine = asyncio.coroutine


def yieldable(future):
    # TODO: really explain.
    return next(iter(future))


def asyncio_motor_sock_method(method):
    """Decorator for socket-like methods on AsyncioMotorSocket.

    The wrapper pauses the current greenlet while I/O is in progress,
    and uses the asyncio event loop to schedule the greenlet for resumption
    when I/O is ready.
    """
    @functools.wraps(method)
    def wrapped_method(self, *args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Should be on child greenlet"

        # This is run by the event loop on the main greenlet when operation
        # completes; switch back to child to continue processing
        def callback(_):
            try:
                res = future.result()
            except asyncio.TimeoutError:
                child_gr.throw(socket.timeout("timed out"))
            except Exception as ex:
                child_gr.throw(ex)
            else:
                child_gr.switch(res)

        coro = method(self, *args, **kwargs)
        if self.timeout:
            coro = asyncio.wait_for(coro, self.timeout, loop=self.loop)
        future = asyncio.async(coro, loop=self.loop)
        future.add_done_callback(callback)
        return main.switch()

    return wrapped_method


class AsyncioMotorSocket:
    """A fake socket instance that pauses and resumes the current greenlet.

    Pauses the calling greenlet when making blocking calls, and uses the
    asyncio event loop to schedule the greenlet for resumption when I/O
    is ready.

    We only implement those socket methods actually used by PyMongo.
    """
    def __init__(self, loop, options):
        self.loop = loop
        self.options = options
        self.timeout = None
        self.ctx = None
        self._writer = None
        self._reader = None

        if options.use_ssl:
            # TODO: cache at Pool level.
            ctx = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            if options.certfile is not None:
                ctx.load_cert_chain(options.certfile, options.keyfile)
            if options.ca_certs is not None:
                ctx.load_verify_locations(options.ca_certs)
            if options.cert_reqs is not None:
                ctx.verify_mode = options.cert_reqs
                if ctx.verify_mode in (ssl.CERT_OPTIONAL, ssl.CERT_REQUIRED):
                    ctx.check_hostname = True

            self.ctx = ctx

    def settimeout(self, timeout):
        self.timeout = timeout

    @asyncio_motor_sock_method
    @asyncio.coroutine
    def connect(self):
        is_unix_socket = (self.options.family == getattr(socket,
                                                         'AF_UNIX', None))
        if is_unix_socket:
            path = self.options.address[0]
            reader, writer = yield from asyncio.open_unix_connection(
                path, loop=self.loop, ssl=self.ctx)
        else:
            host, port = self.options.address
            reader, writer = yield from asyncio.open_connection(
                host=host, port=port, ssl=self.ctx, loop=self.loop)
            sock = writer.transport.get_extra_info('socket')
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE,
                            self.options.socket_keepalive)
        self._reader, self._writer = reader, writer

    def sendall(self, data):
        assert greenlet.getcurrent().parent is not None,\
            "Should be on child greenlet"

        # TODO: backpressure? errors?
        self._writer.write(data)

    @asyncio_motor_sock_method
    @asyncio.coroutine
    def recv(self, num_bytes):
        rv = yield from self._reader.readexactly(num_bytes)
        return rv

    def close(self):
        if self._writer:
            self._writer.close()


# A create_socket() function is part of Motor's framework interface.
create_socket = AsyncioMotorSocket
