# Copyright 2011-2014 MongoDB, Inc.
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
"""asyncio compatibility layer for MongoDB, an asynchronous MongoDB driver."""

import asyncio
import functools
import socket
import sys

import greenlet


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


def call_soon(loop, callback):
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


def get_resolver(loop):
    # asyncio's resolver just calls getaddrinfo in a thread. It's not yet
    # configurable, see https://code.google.com/p/tulip/issues/detail?id=160
    return None


def resolve(resolver, loop, host, port, family, callback, errback):
    def done_callback(future):
        try:
            # TODO: cleanup
            addresses = future.result()
            rv = [
                (af, sa) for af, sock_type, proto, canonname, sa in addresses]

            callback(rv)
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

                self.writer.abort()
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


class AsyncioMotorSocket(object):
    """A fake socket instance that pauses and resumes the current greenlet.

    Pauses the calling greenlet when making blocking calls, and uses the
    asyncio event loop to schedule the greenlet for resumption when I/O is ready.

    We only implement those socket methods actually used by PyMongo.
    """
    def __init__(
            self,
            sock,
            loop,
            use_ssl,
            certfile,
            keyfile,
            ca_certs,
            cert_reqs):
        self.sock = sock
        self.loop = loop
        self.use_ssl = use_ssl
        self.timeout = None
        if self.use_ssl:
            # TODO
            raise NotImplementedError
            #
            # # In Python 3, Tornado's ssl_options_to_context fails if
            # # any options are None.
            # ssl_options = {}
            # if certfile:
            #     ssl_options['certfile'] = certfile
            #
            # if keyfile:
            #     ssl_options['keyfile'] = keyfile
            #
            # if ca_certs:
            #     ssl_options['ca_certs'] = ca_certs
            #
            # if cert_reqs:
            #     ssl_options['cert_reqs'] = cert_reqs
            #
            # self.stream = iostream.SSLIOStream(
            #     sock, ssl_options=ssl_options, io_loop=io_loop)

    def setsockopt(self, *args, **kwargs):
        self.sock.setsockopt(*args, **kwargs)

    def settimeout(self, timeout):
        self.timeout = timeout

    @asyncio_motor_sock_method
    def connect(self, pair, server_hostname=None):
        """
        :Parameters:
         - `pair`: A tuple, (host, port)
        """
        # 'server_hostname' is used for optional certificate validation.
        # TODO: cert validation
        return self.loop.sock_connect(self.sock, pair)

    def sendall(self, data):
        assert greenlet.getcurrent().parent is not None,\
            "Should be on child greenlet"

        # TODO: backpressure? errors?
        self.loop.sock_sendall(self.sock, data)

    @asyncio_motor_sock_method
    def recv(self, num_bytes):
        return self.loop.sock_recv(self.sock, num_bytes)

    def close(self):
        self.sock.close()

    def fileno(self):
        return self.sock.fileno()


# A create_socket() function is part of Motor's framework interface.
create_socket = AsyncioMotorSocket
