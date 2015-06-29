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
import sys

import greenlet
import collections


def get_event_loop():
    return asyncio.get_event_loop()


def is_event_loop(loop):
    # TODO: is there any way to assure that this is an event loop?
    return True


def return_value(value):
    # In Python 3.3, StopIteration can accept a value.
    raise StopIteration(value)


# TODO: rename?
def get_future(loop):
    return asyncio.Future(loop=loop)


def is_future(f):
    return isinstance(f, asyncio.Future)


def call_soon(loop, callback, *args, **kwargs):
    if args or kwargs:
        loop.call_soon(functools.partial(callback, *args, **kwargs))
    else:
        loop.call_soon(callback)


def call_soon_threadsafe(loop, callback):
    loop.call_soon_threadsafe(callback)


def call_later(loop, delay, callback, *args, **kwargs):
    if kwargs:
        return loop.call_later(
            delay,
            functools.partial(callback, *args, **kwargs))
    else:
        return loop.call_later(
            loop.time() + delay,
            callback,
            *args)


def call_later_cancel(loop, handle):
    handle.cancel()


def create_task(loop, coro, *args, **kwargs):
    asyncio.tasks.Task(coro(*args, **kwargs), loop=loop)


def get_resolver(loop):
    # asyncio's resolver just calls getaddrinfo in a thread. It's not yet
    # configurable, see https://code.google.com/p/tulip/issues/detail?id=160
    return None


def resolve(resolver, loop, host, port, family, callback, errback):
    def done_callback(future):
        try:
            addresses = future.result()
            callback(addresses)
        except:
            errback(*sys.exc_info())

    future = loop.getaddrinfo(host, port, family=family)
    future.add_done_callback(done_callback)


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
    def _motor_sock_method(self, *args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Should be on child greenlet"

        future = None
        timeout_handle = None

        if self.timeout:
            def timeout_err():
                if future:
                    future.cancel()

                if self._transport:
                    self._transport.abort()

                child_gr.throw(socket.error("timed out"))

            timeout_handle = self.loop.call_later(self.timeout, timeout_err)

        # This is run by the event loop on the main greenlet when operation
        # completes; switch back to child to continue processing
        def callback(_):
            if timeout_handle:
                timeout_handle.cancel()

            try:
                child_gr.switch(future.result())
            except asyncio.CancelledError:
                # Timeout. We've already thrown an error on the child greenlet.
                pass
            except Exception as ex:
                child_gr.throw(socket.error(str(ex)))

        future = asyncio.async(method(self, *args, **kwargs), loop=self.loop)
        future.add_done_callback(callback)
        return main.switch()

    return _motor_sock_method


class AsyncioMotorSocket(asyncio.Protocol):
    """A fake socket instance that pauses and resumes the current greenlet.

    Pauses the calling greenlet when making blocking calls, and uses the
    asyncio event loop to schedule the greenlet for resumption when I/O is ready.

    We only implement those socket methods actually used by PyMongo.
    """
    def __init__(self, loop, options):
        self.loop = loop
        self.options = options
        self.timeout = None
        self.ctx = None
        self._transport = None
        self._connected_future = asyncio.Future(loop=self.loop)
        self._buffer = collections.deque()
        self._buffer_len = 0
        self._recv_future = asyncio.Future(loop=self.loop)

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
        protocol_factory = lambda: self

        # TODO: will call getaddrinfo again.
        host, port = self.options.address
        self._transport, protocol = yield from self.loop.create_connection(
            protocol_factory, host, port,
            ssl=self.ctx)

    def sendall(self, data):
        assert greenlet.getcurrent().parent is not None,\
            "Should be on child greenlet"

        # TODO: backpressure? errors?
        self._transport.write(data)

    @asyncio_motor_sock_method
    @asyncio.coroutine
    def recv(self, num_bytes):
        while self._buffer_len < num_bytes:
            yield from self._recv_future

        data = bytes().join(self._buffer)
        rv = data[:num_bytes]
        remainder = data[num_bytes:]

        self._buffer.clear()
        if remainder:
            self._buffer.append(remainder)

        self._buffer_len = len(remainder)

        return rv

    def close(self):
        self._transport.close()

    # Protocol interface.
    def connection_made(self, transport):
        pass
        # self._connected_future.set_result(None)

    def data_received(self, data):
        self._buffer_len += len(data)
        self._buffer.append(data)

        # TODO: comment
        future = self._recv_future
        self._recv_future = asyncio.Future(loop=self.loop)
        future.set_result(None)

    def connection_lost(self, exc):
        pass

# A create_socket() function is part of Motor's framework interface.
create_socket = AsyncioMotorSocket
