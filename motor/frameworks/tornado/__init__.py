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

from __future__ import unicode_literals, absolute_import

# TODO: link to framework spec in dev guide.

"""Tornado compatibility layer for MongoDB, an asynchronous MongoDB driver."""

import datetime
import functools
import socket
import sys

import greenlet
import tornado
from tornado import concurrent, gen, ioloop, iostream, netutil

from motor.motor_common import callback_type_error

DomainError = None
try:
    # If Twisted is installed. See resolve().
    from twisted.names.error import DomainError
except ImportError:
    DomainError = None


def get_event_loop():
    return ioloop.IOLoop.current()


def is_event_loop(loop):
    return isinstance(loop, ioloop.IOLoop)


def check_event_loop(loop):
    if not is_event_loop(loop):
        raise TypeError(
            "io_loop must be instance of IOLoop, not %r" % loop)


# Beginning in Tornado 4, TracebackFuture is a deprecated alias for Future.
# Future-proof Motor in case TracebackFuture is some day removed. Remove this
# Future-proofing once we drop support for Tornado 3.
try:
    _TornadoFuture = concurrent.TracebackFuture
except AttributeError:
    _TornadoFuture = concurrent.Future


def get_future(loop):
    return _TornadoFuture()


_DEFAULT = object()


def future_or_callback(future, callback, io_loop, return_value=_DEFAULT):
    """Compatible way to return a value in all Pythons.

    PEP 479, raise StopIteration(value) from a coroutine won't work forever,
    but "return value" doesn't work in Python 2. Instead, Motor methods that
    return values either execute a callback with the value or resolve a Future
    with it, and are implemented with callbacks rather than a coroutine
    internally.
    """
    if callback:
        if not callable(callback):
            raise callback_type_error

        # Motor's callback convention is "callback(result, error)".
        def done_callback(_future):
            try:
                result = _future.result()
                callback(result if return_value is _DEFAULT else return_value,
                         None)
            except Exception as exc:
                callback(None, exc)

        future.add_done_callback(done_callback)

    elif return_value is not _DEFAULT:
        chained = _TornadoFuture()

        def done_callback(_future):
            try:
                result = _future.result()
                chained.set_result(result if return_value is _DEFAULT
                                   else return_value)
            except Exception as exc:
                # TODO: exc_info
                chained.set_exception(exc)

        future.add_done_callback(done_callback)
        return chained

    else:
        return future


def is_future(f):
    return isinstance(f, concurrent.Future)


def call_soon(loop, callback, *args, **kwargs):
    if args or kwargs:
        loop.add_callback(functools.partial(callback, *args, **kwargs))
    else:
        loop.add_callback(callback)


def call_soon_threadsafe(loop, callback):
    loop.add_callback(callback)


def call_later(loop, delay, callback, *args, **kwargs):
    if args or kwargs:
        return loop.add_timeout(
            loop.time() + delay,
            functools.partial(callback, *args, **kwargs))
    else:
        return loop.add_timeout(
            loop.time() + delay,
            callback)


def call_later_cancel(loop, handle):
    loop.remove_timeout(handle)


def create_task(loop, coro, *args, **kwargs):
    loop.add_callback(functools.partial(coro, *args, **kwargs))


def get_resolver(loop):
    return netutil.Resolver(io_loop=loop)


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
            def _callback(_future):
                try:
                    result = _future.result()
                    callback(result, None)
                except Exception as e:
                    callback(None, e)
            future.add_done_callback(_callback)
        else:
            return future
    return wrapper


def pymongo_class_wrapper(f, pymongo_class):
    """Executes the coroutine f and wraps its result in a Motor class.

    See WrapAsync.
    """
    @functools.wraps(f)
    @coroutine
    def _wrapper(self, *args, **kwargs):
        result = yield f(self, *args, **kwargs)

        # Don't call isinstance(), not checking subclasses.
        if result.__class__ == pymongo_class:
            # Delegate to the current object to wrap the result.
            raise gen.Return(self.wrap(result))
        else:
            raise gen.Return(result)

    return _wrapper


def yieldable(future):
    # TODO: really explain.
    return future


timeout_exc = socket.error('timed out')


def tornado_motor_sock_method(method):
    """Decorator for socket-like methods on TornadoMotorSocket.

    The wrapper pauses the current greenlet while I/O is in progress,
    and uses the Tornado IOLoop to schedule the greenlet for resumption
    when I/O is ready.
    """
    coro = gen.coroutine(method)

    @functools.wraps(method)
    def wrapped(self, *args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main is not None, "Should be on child greenlet"

        def callback(future):
            if future.exc_info():
                child_gr.throw(*future.exc_info())
            elif future.exception():
                child_gr.throw(future.exception())
            else:
                child_gr.switch(future.result())

        # Ensure the callback runs on the main greenlet.
        self.io_loop.add_future(coro(self, *args, **kwargs), callback)

        # Pause this greenlet until the coroutine finishes,
        # then return its result or raise its exception.
        return main.switch()

    return wrapped


if tornado.version_info[0] < 4:
    # In Tornado 3.2, IOStream.connect and read_bytes don't return Futures.
    def stream_method(stream, method_name, *args, **kwargs):
        future = concurrent.Future()
        close_callback = functools.partial(
            future.set_exception, socket.error('error'))

        stream.set_close_callback(close_callback)

        def callback(result=None):
            stream.set_close_callback(None)
            future.set_result(result)

        method = getattr(stream, method_name)
        method(*args, callback=callback, **kwargs)
        return future
else:
    # In Tornado 4, IOStream.connect and read_bytes return Futures.
    def stream_method(stream, method_name, *args, **kwargs):
        method = getattr(stream, method_name)
        return method(*args, **kwargs)


def clear_tb_log(future):
    # Avoid "Future exception was never retrieved".
    future.exception()


class _Wait(concurrent.Future):
    """Utility to wait for a Future with a timeout."""
    def __init__(self, future, io_loop, timeout_td, timeout_exception):
        super(_Wait, self).__init__()
        self._io_loop = io_loop
        self._timeout_exception = timeout_exception
        self._timeout_obj = io_loop.add_timeout(timeout_td, self._on_timeout)
        concurrent.chain_future(future, self)
        future.add_done_callback(clear_tb_log)

    def _on_timeout(self):
        self._timeout_obj = None
        self._io_loop = None
        if not self.done():
            self.set_exception(self._timeout_exception)


class TornadoMotorSocket(object):
    """A fake socket instance that pauses and resumes the current greenlet.

    Pauses the calling greenlet when making blocking calls, and uses the
    Tornado IOLoop to schedule the greenlet for resumption when I/O is ready.

    We only implement those socket methods actually used by PyMongo.
    """
    def __init__(self, loop, options):
        self.io_loop = loop
        self.options = options

        # A timedelta or None.
        self.timeout_td = None
        self.stream = None

    def settimeout(self, timeout):
        # IOStream calls socket.setblocking(False), which does settimeout(0.0).
        # We must not allow pymongo to set timeout to some other value (a
        # positive number or None) or the socket will start blocking again.
        # Instead, we simulate timeouts by interrupting ourselves with
        # callbacks.
        if timeout is None:
            self.timeout_td = None
        else:
            self.timeout_td = datetime.timedelta(seconds=timeout)

    @tornado_motor_sock_method
    def connect(self):
        options = self.options

        # socket module doesn't have an AF_UNIX constant on Windows.
        is_unix_socket = (options.family == getattr(socket, 'AF_UNIX', None))
        host, port = options.address
        try:
            if is_unix_socket:
                addrinfos = [(socket.AF_UNIX, host)]
            else:
                addrinfos = yield options.resolver.resolve(host, port,
                                                           options.family)
        except Exception:
            exc_typ, exc_val, exc_tb = sys.exc_info()

            # If netutil.Resolver is configured to use TwistedResolver, raised
            # Twisted's DomainError.
            if DomainError and issubclass(exc_typ, DomainError):
                raise socket.gaierror(str(exc_val))
            else:
                # Already a gaierror.
                raise
        else:
            # Name resolution succeeded.
            # TODO: parallel connection attempts.
            # TODO: Longer-term, do Happy Eyeballs like asyncio.
            err = None
            for af, sock_addr in addrinfos:
                sock, stream = None, None
                try:
                    sock = socket.socket(af)
                    if not is_unix_socket:
                        sock.setsockopt(socket.IPPROTO_TCP,
                                        socket.TCP_NODELAY, 1)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE,
                                        options.socket_keepalive)
                    stream = self._create_stream(sock)
                    future = stream_method(stream, 'connect', sock_addr,
                                           server_hostname=host)

                    if self.timeout_td:
                        yield _Wait(
                            future,
                            self.io_loop,
                            self.timeout_td,
                            timeout_exc)
                    else:
                        yield future

                    # Connection succeeded.
                    self.stream = stream
                    return
                except Exception as e:
                    if sock is not None:
                        sock.close()

                    if stream and stream.error:
                        tmp_err = stream.error
                    else:
                        tmp_err = e

                    # PyMongo expects a socket.error.
                    if isinstance(tmp_err, socket.error):
                        err = tmp_err
                    else:
                        err = socket.error(str(tmp_err))

            if err is not None:
                raise err
            else:
                # This likely means we tried to connect to an IPv6 only
                # host with an OS/kernel or Python interpreter that doesn't
                # support IPv6.
                raise socket.error('getaddrinfo failed')

    def sendall(self, data):
        try:
            self.stream.write(data)
        except IOError as e:
            # PyMongo is built to handle socket.error here, not IOError.
            raise socket.error(str(e))

    @tornado_motor_sock_method
    def recv(self, num_bytes):
        future = stream_method(self.stream, 'read_bytes', num_bytes)
        try:
            if self.timeout_td:
                result = yield _Wait(
                    future,
                    self.io_loop,
                    self.timeout_td,
                    timeout_exc)
            else:
                result = yield future
        except IOError as e:
            # PyMongo is built to handle socket.error here, not IOError.
            raise socket.error(str(e))

        raise gen.Return(result)

    def close(self):
        if not self.stream:
            return

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

    def _create_stream(self, sock):
        if self.options.use_ssl:
            # In Python 3, Tornado's ssl_options_to_context fails if
            # any options are None.
            ssl_options = {}
            if self.options.certfile:
                ssl_options['certfile'] = self.options.certfile

            if self.options.keyfile:
                ssl_options['keyfile'] = self.options.keyfile

            if self.options.ca_certs:
                ssl_options['ca_certs'] = self.options.ca_certs

            if self.options.cert_reqs:
                ssl_options['cert_reqs'] = self.options.cert_reqs

            return iostream.SSLIOStream(
                sock,
                ssl_options=ssl_options,
                io_loop=self.io_loop)
        else:
            return iostream.IOStream(
                sock,
                io_loop=self.io_loop)

    def fileno(self):
        return self.stream.socket.fileno()


# A create_socket() function is part of Motor's framework interface.
create_socket = TornadoMotorSocket
