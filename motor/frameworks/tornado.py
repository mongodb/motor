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

from __future__ import unicode_literals, absolute_import

# TODO: link to framework spec in dev guide.
"""Tornado compatibility layer for MongoDB, an asynchronous MongoDB driver."""

import functools
import socket
import time

import greenlet
from tornado import concurrent, gen, ioloop, iostream, netutil, stack_context

DomainError = None
try:
    # If Twisted is installed. See resolve().
    from twisted.names.error import DomainError
except ImportError:
    pass

from motor.motor_common import callback_type_error


def get_event_loop():
    return ioloop.IOLoop.current()


def is_event_loop(loop):
    return isinstance(loop, ioloop.IOLoop)


def return_value(value):
    raise gen.Return(value)


# TODO: rename?
def get_future():
    return concurrent.TracebackFuture()


def is_future(f):
    return isinstance(f, concurrent.Future)


def call_soon(loop, callback):
    loop.add_callback(callback)


def call_soon_threadsafe(loop, callback):
    loop.add_callback(callback)


def call_later(loop, delay, callback, *args, **kwargs):
    if args or kwargs:
        loop.add_timeout(
            loop.time() + delay,
            functools.partial(callback, *args, **kwargs))
    else:
        loop.add_timeout(
            loop.time() + delay,
            callback)


def call_later_cancel(loop, handle):
    loop.remove_timeout(handle)


def get_resolver(loop):
    return netutil.Resolver(io_loop=loop)


def resolve(resolver, loop, host, port, family, callback, errback):
    def handler(exc_typ, exc_val, exc_tb):
        # If netutil.Resolver is configured to use TwistedResolver.
        if DomainError and issubclass(exc_typ, DomainError):
            exc_typ = socket.gaierror
            exc_val = socket.gaierror(str(exc_val))

        # Depending on the resolver implementation, we could be on any
        # thread or greenlet. Schedule error handling on the main.
        loop.add_callback(functools.partial(errback, exc_typ, exc_val, exc_tb))

        # Don't propagate the exception.
        return True

    with stack_context.ExceptionStackContext(handler):
        resolver.resolve(host, port, family, callback=callback)


def close_resolver(resolver):
    resolver.close()


def coroutine(f):
    """A coroutine that accepts an optional callback.

    Given a callback, the function returns None, and the callback is run
    with (result, error). Without a callback the function returns a Future.
    """
    coro = gen.coroutine(f)

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        callback = kwargs.pop('callback', None)
        if callback and not callable(callback):
            raise callback_type_error
        future = coro(*args, **kwargs)
        if callback:
            def _callback(future):
                try:
                    result = future.result()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
            future.add_done_callback(_callback)
        else:
            return future
    return wrapper


def tornado_motor_sock_method(method):
    """Decorator for socket-like methods on TornadoMotorSocket.

    The wrapper pauses the current greenlet while I/O is in progress,
    and uses the Tornado IOLoop to schedule the greenlet for resumption
    when I/O is ready.
    """
    @functools.wraps(method)
    def _motor_sock_method(self, *args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Should be on child greenlet"

        timeout_object = None

        if self.timeout:
            def timeout_err():
                # Running on the main greenlet. If a timeout error is thrown,
                # we raise the exception on the child greenlet. Closing the
                # IOStream removes callback() from the IOLoop so it isn't
                # called.
                self.stream.set_close_callback(None)
                self.stream.close()
                child_gr.throw(socket.timeout("timed out"))

            timeout_object = self.stream.io_loop.add_timeout(
                time.time() + self.timeout, timeout_err)

        # This is run by IOLoop on the main greenlet when operation
        # completes; switch back to child to continue processing
        def callback(result=None):
            self.stream.set_close_callback(None)
            if timeout_object:
                self.stream.io_loop.remove_timeout(timeout_object)

            child_gr.switch(result)

        # Run on main greenlet
        def closed():
            if timeout_object:
                self.stream.io_loop.remove_timeout(timeout_object)

            # The child greenlet might have died, e.g.:
            # - An operation raised an error within PyMongo
            # - PyMongo closed the MotorSocket in response
            # - MotorSocket.close() closed the IOStream
            # - IOStream scheduled this closed() function on the loop
            # - PyMongo operation completed (with or without error) and
            #       its greenlet terminated
            # - IOLoop runs this function
            if not child_gr.dead:
                child_gr.throw(socket.error("error"))

        self.stream.set_close_callback(closed)

        try:
            kwargs['callback'] = callback

            # method is MotorSocket.open(), recv(), etc. method() begins a
            # non-blocking operation on an IOStream and arranges for
            # callback() to be executed on the main greenlet once the
            # operation has completed.
            method(self, *args, **kwargs)

            # Pause child greenlet until resumed by main greenlet, which
            # will pass the result of the socket operation (data for recv,
            # number of bytes written for sendall) to us.
            return main.switch()
        except socket.error:
            raise
        except IOError as e:
            # If IOStream raises generic IOError (e.g., if operation
            # attempted on closed IOStream), then substitute socket.error,
            # since socket.error is what PyMongo's built to handle. For
            # example, PyMongo will catch socket.error, close the socket,
            # and raise AutoReconnect.
            raise socket.error(str(e))

    return _motor_sock_method


class TornadoMotorSocket(object):
    """A fake socket instance that pauses and resumes the current greenlet.

    Pauses the calling greenlet when making blocking calls, and uses the
    Tornado IOLoop to schedule the greenlet for resumption when I/O is ready.

    We only implement those socket methods actually used by PyMongo.
    """
    def __init__(
            self, sock, io_loop, use_ssl,
            certfile, keyfile, ca_certs, cert_reqs):
        self.use_ssl = use_ssl
        self.timeout = None
        if self.use_ssl:
            # In Python 3, Tornado's ssl_options_to_context fails if
            # any options are None.
            ssl_options = {}
            if certfile:
                ssl_options['certfile'] = certfile

            if keyfile:
                ssl_options['keyfile'] = keyfile

            if ca_certs:
                ssl_options['ca_certs'] = ca_certs

            if cert_reqs:
                ssl_options['cert_reqs'] = cert_reqs

            self.stream = iostream.SSLIOStream(
                sock, ssl_options=ssl_options, io_loop=io_loop)
        else:
            self.stream = iostream.IOStream(sock, io_loop=io_loop)

    def setsockopt(self, *args, **kwargs):
        self.stream.socket.setsockopt(*args, **kwargs)

    def settimeout(self, timeout):
        # IOStream calls socket.setblocking(False), which does settimeout(0.0).
        # We must not allow pymongo to set timeout to some other value (a
        # positive number or None) or the socket will start blocking again.
        # Instead, we simulate timeouts by interrupting ourselves with
        # callbacks.
        self.timeout = timeout

    @tornado_motor_sock_method
    def connect(self, pair, server_hostname=None, callback=None):
        """
        :Parameters:
         - `pair`: A tuple, (host, port)
        """
        # 'server_hostname' is used for optional certificate validation.
        self.stream.connect(pair, callback, server_hostname=server_hostname)

    def sendall(self, data):
        assert greenlet.getcurrent().parent is not None,\
            "Should be on child greenlet"

        try:
            self.stream.write(data)
        except IOError as e:
            # PyMongo is built to handle socket.error here, not IOError
            raise socket.error(str(e))

        if self.stream.closed():
            # Something went wrong while writing
            raise socket.error("write error")

    @tornado_motor_sock_method
    def recv(self, num_bytes, callback):
        self.stream.read_bytes(num_bytes, callback)

    def close(self):
        sock = self.stream.socket
        try:
            self.stream.close()
        except KeyError:
            # Tornado's _impl (epoll, kqueue, ...) has already removed this
            # file descriptor from its dict.
            pass
        finally:
            # Sometimes necessary to avoid ResourceWarnings in Python 3:
            # specifically, if the fd is closed from the OS's view, then
            # stream.close() throws an exception, but the socket still has an
            # fd and so will print a ResourceWarning. In that case, calling
            # sock.close() directly clears the fd and does not raise an error.
            if sock:
                sock.close()

    def fileno(self):
        return self.stream.socket.fileno()


# A create_socket() function is part of Motor's framework interface.
create_socket = TornadoMotorSocket
