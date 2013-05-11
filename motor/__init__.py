# Copyright 2011-2012 10gen, Inc.
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

"""Motor, an asynchronous driver for MongoDB and Tornado."""

import collections
import functools
import inspect
import socket
import time
import sys
import warnings
import weakref

from tornado import ioloop, iostream, gen, stack_context
from tornado.concurrent import Future
import greenlet

import pymongo
import pymongo.common
import pymongo.errors
import pymongo.mongo_client
import pymongo.mongo_replica_set_client
import pymongo.son_manipulator
from pymongo.pool import Pool
import gridfs

from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.cursor import Cursor
from gridfs import grid_file


__all__ = ['MotorClient', 'MotorReplicaSetClient', 'Op']

version_tuple = (0, 1, '+')

def get_version_string():
    if isinstance(version_tuple[-1], basestring):
        return '.'.join(map(str, version_tuple[:-1])) + version_tuple[-1]
    return '.'.join(map(str, version_tuple))

version = get_version_string()
"""Current version of Motor."""


# TODO: ensure we're doing
#   timeouts as efficiently as possible, test performance hit with timeouts
#   from registering and cancelling timeouts


def check_deprecated_kwargs(kwargs):
    if 'safe' in kwargs:
        raise pymongo.errors.ConfigurationError(
            "Motor does not support 'safe', use 'w'")

    if 'slave_okay' in kwargs or 'slaveok' in kwargs:
        raise pymongo.errors.ConfigurationError(
            "Motor does not support 'slave_okay', use read_preference")


callback_type_error = TypeError("callback must be a callable")


def motor_sock_method(method):
    """Wrap a MotorSocket method to pause the current greenlet and arrange
       for the greenlet to be resumed when non-blocking I/O has completed.
    """
    @functools.wraps(method)
    def _motor_sock_method(self, *args, **kwargs):
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main, "Should be on child greenlet"

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
        except IOError, e:
            # If IOStream raises generic IOError (e.g., if operation
            # attempted on closed IOStream), then substitute socket.error,
            # since socket.error is what PyMongo's built to handle. For
            # example, PyMongo will catch socket.error, close the socket,
            # and raise AutoReconnect.
            raise socket.error(str(e))

    return _motor_sock_method


class MotorSocket(object):
    """Replace socket with a class that yields from the current greenlet, if
    we're on a child greenlet, when making blocking calls, and uses Tornado
    IOLoop to schedule child greenlet for resumption when I/O is ready.

    We only implement those socket methods actually used by pymongo.
    """
    def __init__(self, sock, io_loop, use_ssl=False):
        self.use_ssl = use_ssl
        self.timeout = None
        if self.use_ssl:
            self.stream = iostream.SSLIOStream(sock, io_loop=io_loop)
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

    @motor_sock_method
    def connect(self, pair, callback):
        """
        :Parameters:
         - `pair`: A tuple, (host, port)
        """
        self.stream.connect(pair, callback)

    def sendall(self, data):
        assert greenlet.getcurrent().parent, "Should be on child greenlet"
        try:
            self.stream.write(data)
        except IOError, e:
            # PyMongo is built to handle socket.error here, not IOError
            raise socket.error(str(e))

        if self.stream.closed():
            # Something went wrong while writing
            raise socket.error("write error")

    @motor_sock_method
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


class InstanceCounter(object):
    def __init__(self):
        self.refs = set()

    def track(self, instance):
        self.refs.add(weakref.ref(instance, self.untrack))

    def untrack(self, ref):
        self.refs.remove(ref)

    def count(self):
        return len(self.refs)


class MotorPoolTimeout(pymongo.errors.OperationFailure):
    """An operation waited too long to acquire a socket from the pool"""
    pass


class MotorPool(Pool):
    """A pool of MotorSockets.

    Note this sets use_greenlets=True so that when PyMongo internally calls
    start_request, e.g. in MongoClient.copy_database(), this pool assigns a
    socket to the current greenlet for the duration of the method. Request
    semantics are not exposed to Motor's users.
    """
    def __init__(self, io_loop, max_concurrent, max_wait_time, *args, **kwargs):
        kwargs['use_greenlets'] = True
        Pool.__init__(self, *args, **kwargs)
        self.io_loop = io_loop
        self.motor_sock_counter = InstanceCounter()
        self.queue = collections.deque()
        self.waiter_timeouts = {}
        self.max_concurrent = pymongo.common.validate_positive_integer(
            'max_concurrent', max_concurrent)

        self.max_wait_time = max_wait_time
        if self.max_wait_time is not None:
            pymongo.common.validate_positive_float(
                'max_wait_time', self.max_wait_time)

    def create_connection(self, pair):
        """Copy of Pool.create_connection()
        """
        # TODO: refactor all this with Pool, use a new hook to wrap the
        #   socket with MotorSocket before attempting connect().
        host, port = pair or self.pair

        # Check if dealing with a unix domain socket
        if host.endswith('.sock'):
            if not hasattr(socket, "AF_UNIX"):
                raise pymongo.errors.ConnectionFailure(
                    "UNIX-sockets are not supported on this system")
            addrinfos = [(socket.AF_UNIX, socket.SOCK_STREAM, 0, host)]

        else:
            # Don't try IPv6 if we don't support it. Also skip it if host
            # is 'localhost' (::1 is fine). Avoids slow connect issues
            # like PYTHON-356.
            family = socket.AF_INET
            if socket.has_ipv6 and host != 'localhost':
                family = socket.AF_UNSPEC

            addrinfos = [
                (af, socktype, proto, sa) for af, socktype, proto, dummy, sa in
                socket.getaddrinfo(host, port, family, socket.SOCK_STREAM)]

        err = None
        motor_sock = None
        for af, socktype, proto, sa in addrinfos:
            try:
                sock = socket.socket(af, socktype, proto)
                motor_sock = MotorSocket(
                    sock, self.io_loop, use_ssl=self.use_ssl)

                if af != getattr(socket, 'AF_UNIX', None):
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    motor_sock.settimeout(self.conn_timeout or 20.0)

                # Important to increment the count before beginning to connect
                self.motor_sock_counter.track(motor_sock)

                # MotorSocket pauses this greenlet and resumes when connected
                motor_sock.connect(sa)

                return motor_sock
            except socket.error, e:
                err = e
                if motor_sock is not None:
                    motor_sock.close()

        if err is not None:
            raise err
        else:
            # This likely means we tried to connect to an IPv6 only
            # host with an OS/kernel or Python interpreter that doesn't
            # support IPv6.
            raise socket.error('getaddrinfo failed')

    def connect(self, pair):
        """Copy of Pool.connect(), avoiding call to ssl.wrap_socket which
           is inappropriate for Motor.
           TODO: refactor, extra hooks in Pool
        """
        child_gr = greenlet.getcurrent()
        main = child_gr.parent
        assert main, "Should be on child greenlet"

        if self.motor_sock_counter.count() >= self.max_concurrent:
            waiter = stack_context.wrap(child_gr.switch)
            self.queue.append(waiter)

            if self.max_wait_time:
                deadline = time.time() + self.max_wait_time
                timeout = self.io_loop.add_timeout(deadline, functools.partial(
                    child_gr.throw, MotorPoolTimeout, "timeout"))
                self.waiter_timeouts[waiter] = timeout

            # Yield until maybe_return_socket passes spare socket in.
            return main.switch()
        else:
            motor_sock = self.create_connection(pair)
            motor_sock.settimeout(self.net_timeout)
            return pymongo.pool.SocketInfo(motor_sock, self.pool_id)

    def _return_socket(self, sock_info):
        # This is *not* a request socket. Give it to the greenlet at the head
        # of the line, or return it to the pool, or discard it.
        if self.queue:
            waiter = self.queue.popleft()
            if waiter in self.waiter_timeouts:
                self.io_loop.remove_timeout(self.waiter_timeouts.pop(waiter))

            with stack_context.NullContext():
                self.io_loop.add_callback(functools.partial(waiter, sock_info))
        else:
            Pool._return_socket(self, sock_info)


def add_callback_to_future(callback, future):
    """Add a callback with parameters (result, error) to the Future."""
    def cb(future):
        try:
            result = future.result()
        except Exception, e:
            callback(None, e)
            return

        callback(result, None)

    future.add_done_callback(cb)


def callback_from_future(future):
    """Return a callback that sets a Future's result or exception"""
    def callback(result, error):
        if error:
            future.set_exception(error)
        else:
            future.set_result(result)

    return callback


def asynchronize(motor_class, sync_method, has_write_concern, doc=None):
    """Decorate `sync_method` so it accepts a callback or returns a Future.

    The method runs on a child greenlet and calls the callback or resolves
    the Future when the greenlet completes.

    :Parameters:
     - `motor_class`:       Motor class being created, e.g. MotorClient.
     - `sync_method`:       Bound method of pymongo Collection, Database,
                            MongoClient, or Cursor
     - `has_write_concern`: Whether the method accepts getLastError options
     - `doc`:               Optionally override sync_method's docstring
    """
    @functools.wraps(sync_method)
    def method(self, *args, **kwargs):
        check_deprecated_kwargs(kwargs)
        loop = self.get_io_loop()
        callback = kwargs.pop('callback', None)

        if callback:
            if not callable(callback):
                raise callback_type_error
            future = None
        else:
            future = Future()

        def call_method():
            # Runs on child greenlet
            # TODO: ew, performance?
            try:
                result = sync_method(self.delegate, *args, **kwargs)
                if callback:
                    # Schedule callback(result, None) on main greenlet
                    loop.add_callback(functools.partial(
                        callback, result, None))
                else:
                    # Schedule future to be resolved on main greenlet
                    loop.add_callback(functools.partial(
                        future.set_result, result))
            except Exception, e:
                if callback:
                    loop.add_callback(functools.partial(
                        callback, None, e))
                else:
                    loop.add_callback(functools.partial(
                        future.set_exception, e))

        # Start running the operation on a greenlet
        greenlet.greenlet(call_method).switch()
        return future

    # This is for the benefit of motor_extensions.py, which needs this info to
    # generate documentation with Sphinx.
    method.is_async_method = True
    method.has_write_concern = has_write_concern
    name = sync_method.__name__
    if name.startswith('__') and not name.endswith("__"):
        # Mangle, e.g. Cursor.__die -> Cursor._Cursor__die
        classname = motor_class.__delegate_class__.__name__
        name = '_%s%s' % (classname, name)

    method.pymongo_method_name = name
    if doc is not None:
        method.__doc__ = doc

    return method


class MotorAttributeFactory(object):
    """Used by Motor classes to mark attributes that delegate in some way to
    PyMongo. At module import time, each Motor class is created, and MotorMeta
    calls create_attribute() for each attr to create the final class attribute.
    """
    def create_attribute(self, cls, attr_name):
        raise NotImplementedError


class Async(MotorAttributeFactory):
    def __init__(self, has_write_concern):
        """A descriptor that wraps a PyMongo method, such as insert or remove,
        and returns an asynchronous version of the method, which accepts a
        callback or returns a Future.

        :Parameters:
         - `has_write_concern`: Whether the method accepts getLastError options
        """
        super(Async, self).__init__()
        self.has_write_concern = has_write_concern

    def create_attribute(self, cls, attr_name):
        method = getattr(cls.__delegate_class__, attr_name)
        return asynchronize(cls, method, self.has_write_concern)

    def wrap(self, original_class):
        return WrapAsync(self, original_class)

    def unwrap(self, motor_class):
        return UnwrapAsync(self, motor_class)


class WrapBase(MotorAttributeFactory):
    def __init__(self, prop):
        super(WrapBase, self).__init__()
        self.property = prop


class WrapAsync(WrapBase):
    def __init__(self, prop, original_class):
        """Like Async, but before it executes the callback or resolves the
        Future, checks if result is a PyMongo class and wraps it in a Motor
        class. E.g., Motor's map_reduce should pass a MotorCollection instead
        of a PyMongo Collection to the Future. Uses the wrap() method on the
        owner object to do the actual wrapping. E.g.,
        Database.create_collection returns a Collection, so MotorDatabase has:

        create_collection = AsyncCommand().wrap(Collection)

        Once Database.create_collection is done, Motor calls
        MotorDatabase.wrap() on its result, transforming the result from
        Collection to MotorCollection, which is passed to the callback or
        Future.

        :Parameters:
        - `prop`: An Async, the async method to call before wrapping its result
          in a Motor class.
        """
        super(WrapAsync, self).__init__(prop)
        self.original_class = original_class

    def create_attribute(self, cls, attr_name):
        async_method = self.property.create_attribute(cls, attr_name)
        original_class = self.original_class

        @functools.wraps(async_method)
        def wrapper(self, *args, **kwargs):
            callback = kwargs.pop('callback', None)

            def done_callback(result, error):
                if error:
                    callback(None, error)
                    return

                # Don't call isinstance(), not checking subclasses
                if result.__class__ == original_class:
                    # Delegate to the current object to wrap the result
                    new_object = self.wrap(result)
                else:
                    new_object = result

                callback(new_object, None)

            if callback:
                if not callable(callback):
                    raise callback_type_error

                async_method(self, *args, callback=done_callback, **kwargs)
            else:
                future = Future()
                # The final callback run from inside done_callback
                callback = callback_from_future(future)
                async_method(self, *args, callback=done_callback, **kwargs)
                return future

        return wrapper


class UnwrapAsync(WrapBase):
    def __init__(self, prop, motor_class):
        """Like Async, but checks if arguments are Motor classes and unwraps
        them. E.g., Motor's drop_database takes a MotorDatabase, unwraps it,
        and passes a PyMongo Database instead.
        """
        super(UnwrapAsync, self).__init__(prop)
        self.motor_class = motor_class

    def create_attribute(self, cls, attr_name):
        f = self.property.create_attribute(cls, attr_name)
        motor_class = self.motor_class

        def _unwrap_obj(obj):
            if isinstance(motor_class, basestring):
                # Delayed reference - e.g., drop_database is defined before
                # MotorDatabase is, so it was initialized with
                # unwrap('MotorDatabase') instead of unwrap(MotorDatabase).
                actual_motor_class = globals()[motor_class]
            else:
                actual_motor_class = motor_class
            # Don't call isinstance(), not checking subclasses
            if obj.__class__ == actual_motor_class:
                return obj.delegate
            else:
                return obj

        @functools.wraps(f)
        def _f(*args, **kwargs):

            # Call _unwrap_obj on each arg and kwarg before invoking f
            args = [_unwrap_obj(arg) for arg in args]
            kwargs = dict([
                (key, _unwrap_obj(value)) for key, value in kwargs.items()])
            return f(*args, **kwargs)

        return _f


class AsyncRead(Async):
    def __init__(self):
        """A descriptor that wraps a PyMongo read method like find_one() that
        returns a Future.
        """
        Async.__init__(self, has_write_concern=False)


class AsyncWrite(Async):
    def __init__(self):
        """A descriptor that wraps a PyMongo write method like update() that
        accepts getLastError options and returns a Future.
        """
        Async.__init__(self, has_write_concern=True)


class AsyncCommand(Async):
    def __init__(self):
        """A descriptor that wraps a PyMongo command like copy_database() that
        returns a Future and does not accept getLastError options.
        """
        Async.__init__(self, has_write_concern=False)


def check_delegate(obj, attr_name):
    if not obj.delegate:
        raise pymongo.errors.InvalidOperation(
            "Call open() on %s before accessing attribute '%s'" % (
                obj.__class__.__name__, attr_name))


class ReadOnlyPropertyDescriptor(object):
    def __init__(self, attr_name):
        self.attr_name = attr_name

    def __get__(self, obj, objtype):
        if obj:
            check_delegate(obj, self.attr_name)
            return getattr(obj.delegate, self.attr_name)
        else:
            # We're accessing this property on a class, e.g. when Sphinx wants
            # MotorGridOut.md5.__doc__
            return getattr(objtype.__delegate_class__, self.attr_name)

    def __set__(self, obj, val):
        raise AttributeError


class ReadOnlyProperty(MotorAttributeFactory):
    """Creates a readonly attribute on the wrapped PyMongo object"""
    def create_attribute(self, cls, attr_name):
        return ReadOnlyPropertyDescriptor(attr_name)


DelegateMethod = ReadOnlyProperty
"""A method on the wrapped PyMongo object that does no I/O and can be called
synchronously"""


class ReadWritePropertyDescriptor(ReadOnlyPropertyDescriptor):
    def __set__(self, obj, val):
        check_delegate(obj, self.attr_name)
        setattr(obj.delegate, self.attr_name, val)


class ReadWriteProperty(MotorAttributeFactory):
    """Creates a mutable attribute on the wrapped PyMongo object"""
    def create_attribute(self, cls, attr_name):
        return ReadWritePropertyDescriptor(attr_name)


class MotorMeta(type):
    """Initializes a Motor class, calling create_attribute() on all its
    MotorAttributeFactories to create the actual class attributes.
    """
    def __new__(cls, class_name, bases, attrs):
        new_class = type.__new__(cls, class_name, bases, attrs)

        # If new_class has no __delegate_class__, then it's a base like
        # MotorClientBase; don't try to update its attrs, we'll use them
        # for its subclasses like MotorClient.
        if getattr(new_class, '__delegate_class__', None):
            for base in reversed(inspect.getmro(new_class)):
                # Turn attribute factories into real methods or descriptors.
                for name, attr in base.__dict__.items():
                    if isinstance(attr, MotorAttributeFactory):
                        new_class_attr = attr.create_attribute(new_class, name)
                        setattr(new_class, name, new_class_attr)

        return new_class


class MotorBase(object):
    __metaclass__ = MotorMeta

    def __eq__(self, other):
        if (
            isinstance(other, self.__class__)
            and hasattr(self, 'delegate')
            and hasattr(other, 'delegate')
        ):
            return self.delegate == other.delegate
        return NotImplemented

    name                            = ReadOnlyProperty()
    document_class                  = ReadWriteProperty()
    read_preference                 = ReadWriteProperty()
    tag_sets                        = ReadWriteProperty()
    secondary_acceptable_latency_ms = ReadWriteProperty()
    write_concern                   = ReadWriteProperty()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.delegate)


class MotorOpenable(object):
    """Base class for Motor objects that can be initialized in two stages:
    basic setup in __init__ and setup requiring I/O in open(), which
    creates the delegate object.
    """
    __metaclass__ = MotorMeta
    __delegate_class__ = None

    def __init__(self, delegate, io_loop, *args, **kwargs):
        if io_loop:
            if not isinstance(io_loop, ioloop.IOLoop):
                raise TypeError(
                    "io_loop must be instance of IOLoop, not %r" % io_loop)
            self.io_loop = io_loop
        else:
            self.io_loop = ioloop.IOLoop.current()

        self.delegate = delegate

        # Store args and kwargs for when open() is called
        self._init_args = args
        self._init_kwargs = kwargs

    def get_io_loop(self):
        return self.io_loop

    def open(self, callback=None):
        """Actually initialize. Takes an optional callback, or returns a Future
        that resolves to self when opened.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)
        """
        if callback and not callable(callback):
            raise callback_type_error

        if callback:
            self._open(callback=callback)
        else:
            future = Future()
            self._open(callback=callback_from_future(future))
            return future

    def _open(self, callback):
        if self.delegate:
            callback(self, None)  # Already open

        def _connect():
            # Run on child greenlet
            try:
                args, kwargs = self._delegate_init_args()
                self.delegate = self.__delegate_class__(*args, **kwargs)
                callback(self, None)
            except Exception, e:
                callback(None, e)

        # Actually connect on a child greenlet
        gr = greenlet.greenlet(_connect)
        gr.switch()

    def _delegate_init_args(self):
        """Return args, kwargs to create a delegate object"""
        return self._init_args, self._init_kwargs


class MotorClientBase(MotorOpenable, MotorBase):
    """MotorClient and MotorReplicaSetClient common functionality.
    """
    database_names = AsyncRead()
    server_info    = AsyncRead()
    alive          = AsyncRead()
    close_cursor   = AsyncCommand()
    copy_database  = AsyncCommand()
    drop_database  = AsyncCommand().unwrap('MotorDatabase')
    disconnect     = DelegateMethod()
    tz_aware       = ReadOnlyProperty()
    close          = DelegateMethod()
    is_primary     = ReadOnlyProperty()
    is_mongos      = ReadOnlyProperty()
    max_bson_size  = ReadOnlyProperty()
    max_pool_size  = ReadOnlyProperty()

    def __init__(self, delegate, io_loop, *args, **kwargs):
        check_deprecated_kwargs(kwargs)
        self._max_concurrent = kwargs.pop('max_concurrent', 100)
        self._max_wait_time = kwargs.pop('max_wait_time', None)
        super(MotorClientBase, self).__init__(
            delegate, io_loop, *args, **kwargs)

    def open_sync(self):
        """Synchronous open(), returning self.

        Under the hood, this method creates a new Tornado IOLoop, runs
        :meth:`open` on the loop, and deletes the loop when :meth:`open`
        completes.
        """
        if self.connected:
            return self

        # Run a private IOLoop until connected or error
        private_loop = ioloop.IOLoop()
        standard_loop, self.io_loop = self.io_loop, private_loop
        try:
            private_loop.run_sync(self.open)
            return self
        finally:
            # Replace the private IOLoop with the default loop
            self.io_loop = standard_loop
            if self.delegate:
                self.delegate.pool_class = functools.partial(
                    MotorPool, self.io_loop,
                    self._max_concurrent, self._max_wait_time)

                for pool in self._get_pools():
                    pool.io_loop = self.io_loop
                    pool.reset()

            # Clean up file descriptors.
            private_loop.close()

    def sync_client(self):
        """Get a PyMongo MongoClient / MongoReplicaSetClient with the same
        configuration as this MotorClient / MotorReplicaSetClient.
        """
        return self.__delegate_class__(
            *self._init_args, **self._init_kwargs)

    def __getattr__(self, name):
        if not self.connected:
            msg = (
                "Can't access attribute '%s' on %s before calling open()"
                " or open_sync()" % (name, self.__class__.__name__))
            raise pymongo.errors.InvalidOperation(msg)

        return MotorDatabase(self, name)

    __getitem__ = __getattr__

    def start_request(self):
        raise NotImplementedError("Motor doesn't implement requests")

    in_request = end_request = start_request

    @property
    def connected(self):
        """True after :meth:`open` or :meth:`open_sync` completes"""
        return self.delegate is not None

    def _delegate_init_args(self):
        """Override MotorOpenable._delegate_init_args to ensure
           auto_start_request is False and _pool_class is MotorPool.
        """
        kwargs = self._init_kwargs.copy()
        kwargs['auto_start_request'] = False
        kwargs['_pool_class'] = functools.partial(
            MotorPool, self.io_loop, self._max_concurrent, self._max_wait_time)
        return self._init_args, kwargs


class MotorClient(MotorClientBase):
    __delegate_class__ = pymongo.mongo_client.MongoClient

    kill_cursors = AsyncCommand()
    fsync        = AsyncCommand()
    unlock       = AsyncCommand()
    nodes        = ReadOnlyProperty()
    host         = ReadOnlyProperty()
    port         = ReadOnlyProperty()

    def __init__(self, *args, **kwargs):
        """Create a new connection to a single MongoDB instance at *host:port*.

        :meth:`open` or :meth:`open_sync` must be called before using a new
        MotorClient. No property access is allowed before the connection
        is opened.

        MotorClient takes the same constructor arguments as
        `MongoClient`_, as well as:

        :Parameters:
          - `io_loop` (optional): Special :class:`tornado.ioloop.IOLoop`
            instance to use instead of default
          - `max_concurrent` (optional): Most connections open at once, default
            100.
          - `max_wait_time` (optional): How long an operation can wait for a
            connection before raising :exc:`MotorPoolTimeout`, default no
            timeout.

        .. _MongoClient: http://api.mongodb.org/python/current/api/pymongo/mongo_client.html
        """
        super(MotorClient, self).__init__(
            None, kwargs.pop('io_loop', None), *args, **kwargs)

    def is_locked(self):
        """Returns a Future that resolves to ``True`` if this server is locked,
        otherwise ``False``. While locked, all write operations are blocked,
        although read operations may still be allowed.

        Use :meth:`fsync` to lock, :meth:`unlock` to unlock::

            @gen.coroutine
            def lock_unlock():
                c = yield motor.MotorClient().open()
                locked = yield c.is_locked()
                assert locked is False
                yield c.fsync(lock=True)
                assert (yield c.is_locked()) is True
                yield c.unlock()
                assert (yield c.is_locked()) is False

        .. note:: PyMongo's :attr:`~pymongo.mongo_client.MongoClient.is_locked`
           is a property that synchronously executes the `currentOp` command on
           the server before returning. In Motor, `is_locked` returns a Future
           and executes asynchronously.
        """
        future = Future()

        def is_locked(current_op_future):
            try:
                result = bool(current_op_future.result().get('fsyncLock', None))
            except Exception, e:
                future.set_exception(e)
                return

            future.set_result(result)

        self.admin.current_op().add_done_callback(is_locked)
        return future

    def _get_pools(self):
        # TODO: expose the PyMongo pool, or otherwise avoid this
        return [self.delegate._MongoClient__pool]


class MotorReplicaSetClient(MotorClientBase):
    __delegate_class__ = pymongo.mongo_replica_set_client.MongoReplicaSetClient

    primary     = ReadOnlyProperty()
    secondaries = ReadOnlyProperty()
    arbiters    = ReadOnlyProperty()
    hosts       = ReadOnlyProperty()
    seeds       = ReadOnlyProperty()
    close       = DelegateMethod()

    def __init__(self, *args, **kwargs):
        """Create a new connection to a MongoDB replica set.

        :meth:`open` or :meth:`open_sync` must be called before using a new
        MotorReplicaSetClient. No property access is allowed before the
        connection is opened.

        MotorReplicaSetClient takes the same constructor arguments as
        `MongoReplicaSetClient`_, as well as:

        :Parameters:
          - `io_loop` (optional): Special :class:`tornado.ioloop.IOLoop`
            instance to use instead of default
          - `max_concurrent` (optional): Most connections open at once, default
            100.
          - `max_wait_time` (optional): How long an operation can wait for a
            connection before raising :exc:`MotorPoolTimeout`, default no
            timeout.

        .. _MongoReplicaSetClient: http://api.mongodb.org/python/current/api/pymongo/mongo_replica_set_client.html
        """
        super(MotorReplicaSetClient, self).__init__(
            None, kwargs.pop('io_loop', None), *args, **kwargs)

    def open_sync(self):
        """Synchronous open(), returning self.

        Under the hood, this method creates a new Tornado IOLoop, runs
        :meth:`open` on the loop, and deletes the loop when :meth:`open`
        completes.
        """
        super(MotorReplicaSetClient, self).open_sync()

        # We need to wait for open_sync() to complete and restore the
        # original IOLoop before starting the monitor.
        self.delegate._MongoReplicaSetClient__monitor.start_motor(self.io_loop)
        return self

    def open(self, callback=None):
        """Actually initialize. Takes an optional callback, or returns a Future
        that resolves to self when opened.

        :Parameters:
         - `callback`: Optional function taking parameters (self, error)
        """
        if callback and not callable(callback):
            raise callback_type_error

        def opened(self, error):
            if error:
                callback(None, error)
            else:
                try:
                    monitor = self.delegate._MongoReplicaSetClient__monitor
                    monitor.start_motor(self.io_loop)
                except Exception, e:
                    callback(None, e)
                else:
                    callback(self, None)  # No errors

        if callback:
            super(MotorReplicaSetClient, self)._open(callback=opened)
        else:
            future = Future()
            # The final callback run from inside opened
            callback = callback_from_future(future)
            super(MotorReplicaSetClient, self)._open(callback=opened)
            return future

    def _delegate_init_args(self):
        # This _monitor_class will be passed to PyMongo's
        # MongoReplicaSetClient when we create it.
        args, kwargs = super(
            MotorReplicaSetClient, self)._delegate_init_args()
        kwargs['_monitor_class'] = MotorReplicaSetMonitor
        return args, kwargs

    def _get_pools(self):
        # TODO: expose the PyMongo RSC members, or otherwise avoid this
        return [
            member.pool for member in
            self.delegate._MongoReplicaSetClient__members.values()]


# PyMongo uses a background thread to regularly inspect the replica set and
# monitor it for changes. In Motor, use a periodic callback on the IOLoop to
# monitor the set.
class MotorReplicaSetMonitor(pymongo.mongo_replica_set_client.Monitor):
    def __init__(self, rsc):
        assert isinstance(
            rsc, pymongo.mongo_replica_set_client.MongoReplicaSetClient
        ), (
            "First argument to MotorReplicaSetMonitor must be"
            " MongoReplicaSetClient, not %r" % rsc)

        # Fake the event_class: we won't use it
        pymongo.mongo_replica_set_client.Monitor.__init__(
            self, rsc, event_class=object)

        self.timeout_obj = None

    def shutdown(self, dummy=None):
        if self.timeout_obj:
            self.io_loop.remove_timeout(self.timeout_obj)

    def refresh(self):
        assert greenlet.getcurrent().parent, "Should be on child greenlet"
        try:
            self.rsc.refresh()
        except pymongo.errors.AutoReconnect:
            pass
        # RSC has been collected or there
        # was an unexpected error.
        except:
            return

        self.timeout_obj = self.io_loop.add_timeout(
            time.time() + self._refresh_interval, self.async_refresh)

    def async_refresh(self):
        greenlet.greenlet(self.refresh).switch()

    def start(self):
        """No-op: PyMongo thinks this starts the monitor, but Motor starts
           the monitor separately to ensure it uses the right IOLoop"""
        pass

    def start_motor(self, io_loop):
        self.io_loop = io_loop
        self.timeout_obj = self.io_loop.add_timeout(
            time.time() + self._refresh_interval, self.async_refresh)

    def schedule_refresh(self):
        if self.io_loop and self.async_refresh:
            if self.timeout_obj:
                self.io_loop.remove_timeout(self.timeout_obj)

            self.io_loop.add_callback(self.async_refresh)

    def join(self, timeout=None):
        # PyMongo calls join() after shutdown() -- this is not a thread, so
        # shutdown works immediately and join is unnecessary
        pass


class MotorDatabase(MotorBase):
    __delegate_class__ = Database

    set_profiling_level = AsyncCommand()
    reset_error_history = AsyncCommand()
    add_user            = AsyncCommand()
    remove_user         = AsyncCommand()
    logout              = AsyncCommand()
    command             = AsyncCommand()
    authenticate        = AsyncCommand()
    eval                = AsyncCommand()
    create_collection   = AsyncCommand().wrap(Collection)
    drop_collection     = AsyncCommand().unwrap('MotorCollection')
    validate_collection = AsyncRead().unwrap('MotorCollection')
    collection_names    = AsyncRead()
    current_op          = AsyncRead()
    profiling_level     = AsyncRead()
    profiling_info      = AsyncRead()
    error               = AsyncRead()
    last_status         = AsyncRead()
    previous_error      = AsyncRead()
    dereference         = AsyncRead()

    incoming_manipulators         = ReadOnlyProperty()
    incoming_copying_manipulators = ReadOnlyProperty()
    outgoing_manipulators         = ReadOnlyProperty()
    outgoing_copying_manipulators = ReadOnlyProperty()

    def __init__(self, connection, name):
        if not isinstance(connection, MotorClientBase):
            raise TypeError("First argument to MotorDatabase must be "
                            "MotorClientBase, not %r" % connection)

        self.connection = connection
        self.delegate = Database(connection.delegate, name)

    def __getattr__(self, name):
        return MotorCollection(self, name)

    __getitem__ = __getattr__

    def wrap(self, collection):
        # Replace pymongo.collection.Collection with MotorCollection
        return self[collection.name]

    def add_son_manipulator(self, manipulator):
        """Add a new son manipulator to this database.

        Newly added manipulators will be applied before existing ones.

        :Parameters:
          - `manipulator`: the manipulator to add
        """
        # We override add_son_manipulator to unwrap the AutoReference's
        # database attribute.
        if isinstance(manipulator, pymongo.son_manipulator.AutoReference):
            db = manipulator.database
            if isinstance(db, MotorDatabase):
                manipulator.database = db.delegate

        self.delegate.add_son_manipulator(manipulator)

    def get_io_loop(self):
        return self.connection.get_io_loop()


class MotorCollection(MotorBase):
    __delegate_class__ = Collection

    create_index      = AsyncCommand()
    drop_indexes      = AsyncCommand()
    drop_index        = AsyncCommand()
    drop              = AsyncCommand()
    ensure_index      = AsyncCommand()
    reindex           = AsyncCommand()
    rename            = AsyncCommand()
    find_and_modify   = AsyncCommand()
    map_reduce        = AsyncCommand().wrap(Collection)
    update            = AsyncWrite()
    insert            = AsyncWrite()
    remove            = AsyncWrite()
    save              = AsyncWrite()
    index_information = AsyncRead()
    count             = AsyncRead()
    options           = AsyncRead()
    group             = AsyncRead()
    distinct          = AsyncRead()
    inline_map_reduce = AsyncRead()
    find_one          = AsyncRead()
    aggregate         = AsyncRead()
    uuid_subtype      = ReadWriteProperty()
    full_name         = ReadOnlyProperty()

    def __init__(self, database, name=None, *args, **kwargs):
        if isinstance(database, Collection):
            # Short cut
            self.delegate = Collection
        elif not isinstance(database, MotorDatabase):
            raise TypeError("First argument to MotorCollection must be "
                            "MotorDatabase, not %r" % database)
        else:
            self.database = database
            self.delegate = Collection(self.database.delegate, name)

    def __getattr__(self, name):
        # dotted collection name, like foo.bar
        return MotorCollection(
            self.database,
            self.name + '.' + name
        )

    def find(self, *args, **kwargs):
        """Create a :class:`MotorCursor`. Same parameters as for
        PyMongo's `find`_.

        Note that :meth:`find` does not take a `callback` parameter--pass
        a callback to the :class:`MotorCursor`'s methods such as
        :meth:`MotorCursor.to_list` or :meth:`MotorCursor.count`.

        .. _find: http://api.mongodb.org/python/current/api/pymongo/collection.html#pymongo.collection.Collection.find
        """
        if 'callback' in kwargs:
            raise pymongo.errors.InvalidOperation(
                "Pass a callback to each, to_list, or count, not to find.")

        cursor = self.delegate.find(*args, **kwargs)
        return MotorCursor(cursor, self)

    def wrap(self, collection):
        # Replace pymongo.collection.Collection with MotorCollection
        return self.database[collection.name]

    def get_io_loop(self):
        return self.database.get_io_loop()


class MotorCursorChainingMethod(MotorAttributeFactory):
    def create_attribute(self, cls, attr_name):
        cursor_method = getattr(Cursor, attr_name)

        @functools.wraps(cursor_method)
        def return_clone(self, *args, **kwargs):
            cursor_method(self.delegate, *args, **kwargs)
            return self

        # This is for the benefit of motor_extensions.py
        return_clone.is_motorcursor_chaining_method = True
        return_clone.pymongo_method_name = attr_name
        return return_clone


class MotorCursor(MotorBase):
    __delegate_class__ = Cursor
    count         = AsyncRead()
    distinct      = AsyncRead()
    explain       = AsyncRead()
    _refresh      = AsyncRead()
    cursor_id     = ReadOnlyProperty()
    alive         = ReadOnlyProperty()
    batch_size    = MotorCursorChainingMethod()
    add_option    = MotorCursorChainingMethod()
    remove_option = MotorCursorChainingMethod()
    limit         = MotorCursorChainingMethod()
    skip          = MotorCursorChainingMethod()
    max_scan      = MotorCursorChainingMethod()
    sort          = MotorCursorChainingMethod()
    hint          = MotorCursorChainingMethod()
    where         = MotorCursorChainingMethod()

    _Cursor__die  = AsyncCommand()

    def __init__(self, cursor, collection):
        """You don't construct a MotorCursor yourself, but acquire one from
        :meth:`MotorCollection.find`.

        .. note::
          There is no need to manually close cursors; they are closed
          by the server after being fully iterated
          with :meth:`to_list`, :meth:`each`, or :meth:`fetch_next`, or
          automatically closed by the client when the :class:`MotorCursor` is
          cleaned up by the garbage collector.
        """
        self.delegate = cursor
        self.collection = collection
        self.started = False
        self.closed = False

    def _get_more(self, callback):
        """
        Get a batch of data asynchronously, either performing an initial query
        or getting more data from an existing cursor.
        :Parameters:
         - `callback`:    function taking parameters (batch_size, error)
        """
        if not self.alive:
            raise pymongo.errors.InvalidOperation(
                "Can't call get_more() on a MotorCursor that has been"
                " exhausted or killed.")

        self.started = True
        self._refresh(callback=callback)

    @property
    def fetch_next(self):
        """Used with `gen.coroutine`_ to asynchronously retrieve the next
        document in the result set, fetching a batch of documents from the
        server if necessary. Yields ``False`` if there are no more documents,
        otherwise :meth:`next_object` is guaranteed to return a document.

        .. _`gen.coroutine`: http://www.tornadoweb.org/documentation/gen.html

        .. testsetup:: fetch_next

          MongoClient().test.test_collection.remove()
          collection = MotorClient().open_sync().test.test_collection

        .. doctest:: fetch_next

          >>> @gen.coroutine
          ... def f():
          ...     yield collection.insert([{'_id': i} for i in range(5)])
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     while (yield cursor.fetch_next):
          ...         doc = cursor.next_object()
          ...         sys.stdout.write(str(doc['_id']) + ', ')
          ...     print 'done'
          ...
          >>> IOLoop.current().run_sync(f)
          0, 1, 2, 3, 4, done

        .. note:: While it appears that fetch_next retrieves each document from
          the server individually, the cursor actually fetches documents
          efficiently in `large batches`_.

        .. _`large batches`: http://docs.mongodb.org/manual/core/read-operations/#cursor-behaviors
        """
        future = Future()

        if not self._buffer_size() and self.alive:
            if self.delegate._Cursor__empty:
                # Special case, limit of 0
                future.set_result(False)
                return future

            def cb(batch_size, error):
                if error:
                    future.set_exception(error)
                else:
                    future.set_result(bool(batch_size))

            self._get_more(cb)
            return future
        elif self._buffer_size():
            future.set_result(True)
            return future
        else:
            # Dead
            future.set_result(False)
        return future

    def next_object(self):
        """Get a document from the most recently fetched batch, or ``None``.
        See :attr:`fetch_next`.
        """
        # __empty is a special case: limit of 0
        if self.delegate._Cursor__empty or not self._buffer_size():
            return None
        return self.delegate.next()

    def each(self, callback):
        """Iterates over all the documents for this cursor.

        `each` returns immediately, and `callback` is executed asynchronously
        for each document. `callback` is passed ``(None, None)`` when iteration
        is complete.

        Cancel iteration early by returning ``False`` from the callback. (Only
        ``False`` cancels iteration: returning ``None`` or 0 does not.)

        .. testsetup:: each

          MongoClient().test.test_collection.remove()
          collection = MotorClient().open_sync().test.test_collection

        .. doctest:: each

          >>> from tornado.ioloop import IOLoop
          >>> collection = MotorClient().open_sync().test.collection
          >>> def inserted(result, error):
          ...     global cursor
          ...     if error:
          ...         raise error
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     cursor.each(callback=each)
          ...
          >>> def each(result, error):
          ...     if error:
          ...         raise error
          ...     elif result:
          ...         sys.stdout.write(str(result['_id']) + ', ')
          ...     else:
          ...         # Iteration complete
          ...         IOLoop.current().stop()
          ...         print 'done'
          ...
          >>> collection.insert(
          ...     [{'_id': i} for i in range(5)], callback=inserted)
          >>> IOLoop.current().start()
          0, 1, 2, 3, 4, done

        .. note:: :meth:`to_list` or :attr:`fetch_next` are much easier to use.

        :Parameters:
         - `callback`: function taking (document, error)
        """
        if not callable(callback):
            raise callback_type_error

        self._each_got_more(callback, None, None)

    def _each_got_more(self, callback, batch_size, error):
        if error:
            callback(None, error)
            return

        add_callback = self.get_io_loop().add_callback

        while self._buffer_size() > 0:
            try:
                doc = self.delegate.next()  # decrements self.buffer_size
            except StopIteration:
                # Special case: limit of 0
                add_callback(functools.partial(callback, None, None))
                self.close()
                return

            # Quit if callback returns exactly False (not None). Note we
            # don't close the cursor: user may want to resume iteration.
            if callback(doc, None) is False:
                return

        if self.alive and (self.cursor_id or not self.started):
            self._get_more(functools.partial(self._each_got_more, callback))
        else:
            # Complete
            add_callback(functools.partial(callback, None, None))

    def to_list(self, length, callback=None):
        """Get a list of documents.

        .. testsetup:: to_list

          MongoClient().test.test_collection.remove()
          collection = MotorClient().open_sync().test.test_collection

        .. doctest:: to_list

          >>> @gen.coroutine
          ... def f():
          ...     yield collection.insert([{'_id': i} for i in range(4)])
          ...     cursor = collection.find().sort([('_id', 1)])
          ...     docs = yield cursor.to_list(length=2)
          ...     while docs:
          ...         print docs
          ...         docs = (yield cursor.to_list(length=2))
          ...
          ...     print 'done'
          ...
          >>> IOLoop.current().run_sync(f)
          [{u'_id': 0}, {u'_id': 1}]
          [{u'_id': 2}, {u'_id': 3}]
          done

        :Parameters:
         - `length`: maximum number of documents to return for this call
         - `callback`: function taking (document, error)

        .. versionchanged:: 0.2
           `length` parameter is no longer optional.
        """
        length = pymongo.common.validate_positive_integer('length', length)

        if self.delegate._Cursor__tailable:
            raise pymongo.errors.InvalidOperation(
                "Can't call to_list on tailable cursor")

        if callback and not callable(callback):
            raise callback_type_error

        # Special case: limit of 0.
        if self.delegate._Cursor__empty:
            if callback:
                callback([], None)
            else:
                future = Future()
                future.set_result(None)
                return future

        the_list = []
        if callback:
            self._to_list_got_more(callback, the_list, length, None, None)
        else:
            future = Future()
            self._to_list_got_more(
                callback_from_future(future), the_list, length, None, None)

            return future

    def _to_list_got_more(self, callback, the_list, length, batch_size, error):
        if error:
            callback(None, error)
            return

        collection = self.collection
        fix_outgoing = collection.database.delegate._fix_outgoing

        if length is None:
            # No maximum length, get all results, apply outgoing manipulators
            results = (fix_outgoing(data, collection) for data in self.delegate._Cursor__data)
            the_list.extend(results)
            self.delegate._Cursor__data.clear()
        else:
            while self._buffer_size() > 0 and len(the_list) < length:
                the_list.append(fix_outgoing(self.delegate._Cursor__data.popleft(), collection))

        if (not self.delegate._Cursor__killed
                and (self.cursor_id or not self.started)
                and (length is None or length > len(the_list))):
            get_more_cb = functools.partial(
                self._to_list_got_more, callback, the_list, length)
            self._get_more(callback=get_more_cb)
        else:
            callback(the_list, None)

    def clone(self):
        """Get a clone of this cursor."""
        return MotorCursor(self.delegate.clone(), self.collection)

    def rewind(self):
        """Rewind this cursor to its unevaluated state."""
        self.delegate.rewind()
        self.started = False
        return self

    def get_io_loop(self):
        return self.collection.get_io_loop()

    def close(self, callback=None):
        """Explicitly kill this cursor on the server, and cease iterating with
        :meth:`each`. Returns a Future.
        """
        self.closed = True
        return self._Cursor__die(callback=callback)

    def __getitem__(self, index):
        """Get a slice of documents from this cursor.

        Raises :class:`~pymongo.errors.InvalidOperation` if this
        cursor has already been used.

        To get a single document use an integral index, e.g.:

        .. testsetup:: getitem

          MongoClient().test.test_collection.remove()
          collection = MotorClient().open_sync().test.test_collection

        .. doctest:: getitem

          >>> @gen.coroutine
          ... def fifth_item():
          ...     yield collection.insert([{'i': i} for i in range(10)])
          ...     cursor = collection.find().sort([('i', 1)])[5]
          ...     yield cursor.fetch_next
          ...     doc = cursor.next_object()
          ...     print doc['i']
          ...
          >>> IOLoop.current().run_sync(fifth_item)
          5

        Any limit previously applied to this cursor will be ignored.

        The cursor returns ``None`` if the index is greater than or equal to
        the length of the result set.

        .. doctest:: getitem

          >>> @gen.coroutine
          ... def one_thousandth_item():
          ...     cursor = collection.find().sort([('i', 1)])[1000]
          ...     yield cursor.fetch_next
          ...     print cursor.next_object()
          ...
          >>> IOLoop.current().run_sync(one_thousandth_item)
          None

        To get a slice of documents use a slice index like
        ``cursor[start:end]``.

        .. doctest:: getitem

          >>> @gen.coroutine
          ... def second_through_fifth_item():
          ...     cursor = collection.find().sort([('i', 1)])[2:6]
          ...     while (yield cursor.fetch_next):
          ...         doc = cursor.next_object()
          ...         sys.stdout.write(str(doc['i']) + ', ')
          ...     print 'done'
          ...
          >>> IOLoop.current().run_sync(second_through_fifth_item)
          2, 3, 4, 5, done

        This will apply a skip of 2 and a limit of 4 to the cursor. Using a
        slice index overrides prior limits or skips applied to this cursor
        (including those applied through previous calls to this method).

        Raises :class:`~pymongo.errors.IndexError` when the slice has a step,
        a negative start value, or a stop value less than or equal to
        the start value.

        :Parameters:
          - `index`: An integer or slice index to be applied to this cursor
        """
        self._check_not_started()
        if isinstance(index, slice):
            # Slicing a cursor does no I/O - it just sets skip and limit - so
            # we can slice it immediately.
            self.delegate[index]
            return self
        else:
            if not isinstance(index, (int, long)):
                raise TypeError("index %r cannot be applied to MotorCursor "
                                "instances" % index)

            # Get one document, force hard limit of 1 so server closes cursor
            # immediately
            return self[self.delegate._Cursor__skip + index:].limit(-1)

    def _buffer_size(self):
        # TODO: expose so we don't have to use double-underscore hack
        return len(self.delegate._Cursor__data)

    def _check_not_started(self):
        if self.started:
            raise pymongo.errors.InvalidOperation(
                "MotorCursor already started")

    def __copy__(self):
        return MotorCursor(self.delegate.__copy__(), self.collection)

    def __deepcopy__(self, memo):
        return MotorCursor(self.delegate.__deepcopy__(memo), self.collection)

    def __del__(self):
        # This MotorCursor is deleted on whatever greenlet does the last
        # decref, or (if it's referenced from a cycle) whichever is current
        # when the GC kicks in. We may need to send the server a killCursors
        # message, but in Motor only direct children of the main greenlet can
        # do I/O. First, do a quick check whether the cursor is still alive on
        # the server:
        if self.cursor_id and self.alive:
            if greenlet.getcurrent().parent:
                # We're on a child greenlet, send the message.
                self.delegate.close()
            else:
                # We're on the main greenlet, start the operation on a child.
                self.close()


class MotorGridOut(MotorOpenable):
    """Class to read data out of GridFS.

       Application developers should generally not need to
       instantiate this class directly - instead see the methods
       provided by :class:`~motor.MotorGridFS`.
    """
    __delegate_class__ = gridfs.GridOut

    __getattr__     = DelegateMethod()
    _id             = ReadOnlyProperty()
    filename        = ReadOnlyProperty()
    name            = ReadOnlyProperty()
    content_type    = ReadOnlyProperty()
    length          = ReadOnlyProperty()
    chunk_size      = ReadOnlyProperty()
    upload_date     = ReadOnlyProperty()
    aliases         = ReadOnlyProperty()
    metadata        = ReadOnlyProperty()
    md5             = ReadOnlyProperty()
    tell            = DelegateMethod()
    seek            = DelegateMethod()
    read            = AsyncRead()
    readline        = AsyncRead()

    def __init__(
        self, root_collection, file_id=None, file_document=None,
        io_loop=None
    ):
        if isinstance(root_collection, grid_file.GridOut):
            # Short cut
            super(MotorGridOut, self).__init__(root_collection, io_loop)
        else:
            if not isinstance(root_collection, MotorCollection):
                raise TypeError(
                    "First argument to MotorGridOut must be "
                    "MotorCollection, not %r" % root_collection)

            assert io_loop is None, \
                "Can't override IOLoop for MotorGridOut"

            super(MotorGridOut, self).__init__(
                None, root_collection.get_io_loop(), root_collection.delegate,
                file_id, file_document)

    @gen.coroutine
    def stream_to_handler(self, request_handler):
        """Write the contents of this file to a
        :class:`tornado.web.RequestHandler`. This method will call `flush` on
        the RequestHandler, so ensure all headers have already been set.
        For a more complete example see the implementation of
        :class:`~motor.web.GridFSHandler`.

        Returns a Future.

        .. code-block:: python

            class FileHandler(tornado.web.RequestHandler):
                @tornado.web.asynchronous
                @gen.coroutine
                def get(self, filename):
                    db = self.settings['db']
                    fs = yield motor.MotorGridFS(db()).open()
                    try:
                        gridout = yield fs.get_last_version(filename)
                    except gridfs.NoFile:
                        raise tornado.web.HTTPError(404)

                    self.set_header("Content-Type", gridout.content_type)
                    self.set_header("Content-Length", gridout.length)
                    yield gridout.stream_to_handler(self)
                    self.finish()

        .. seealso:: Tornado `RequestHandler <http://www.tornadoweb.org/documentation/web.html#request-handlers>`_
        """
        written = 0
        while written < self.length:
            # Reading chunk_size at a time minimizes buffering
            chunk = yield self.read(self.chunk_size)

            # write() simply appends the output to a list; flush() sends it
            # over the network and minimizes buffering in the handler.
            request_handler.write(chunk)
            request_handler.flush()
            written += len(chunk)


class MotorGridIn(MotorOpenable):
    __delegate_class__ = gridfs.GridIn

    __getattr__     = DelegateMethod()
    closed          = ReadOnlyProperty()
    close           = AsyncCommand()
    write           = AsyncCommand().unwrap(MotorGridOut)
    writelines      = AsyncCommand().unwrap(MotorGridOut)
    _id             = ReadOnlyProperty()
    md5             = ReadOnlyProperty()
    filename        = ReadOnlyProperty()
    name            = ReadOnlyProperty()
    content_type    = ReadOnlyProperty()
    length          = ReadOnlyProperty()
    chunk_size      = ReadOnlyProperty()
    upload_date     = ReadOnlyProperty()

    def __init__(self, root_collection, **kwargs):
        """
        Class to write data to GridFS. If instantiating directly, you must call
        :meth:`open` before using the `MotorGridIn` object. However,
        application developers should not generally need to instantiate this
        class - see :meth:`~motor.MotorGridFS.new_file`.

        Any of the file level options specified in the `GridFS Spec
        <http://dochub.mongodb.org/core/gridfsspec>`_ may be passed as
        keyword arguments. Any additional keyword arguments will be
        set as additional fields on the file document. Valid keyword
        arguments include:

          - ``"_id"``: unique ID for this file (default:
            :class:`~bson.objectid.ObjectId`) - this ``"_id"`` must
            not have already been used for another file

          - ``"filename"``: human name for the file

          - ``"contentType"`` or ``"content_type"``: valid mime-type
            for the file

          - ``"chunkSize"`` or ``"chunk_size"``: size of each of the
            chunks, in bytes (default: 256 kb)

          - ``"encoding"``: encoding used for this file. In Python 2,
            any :class:`unicode` that is written to the file will be
            converted to a :class:`str`. In Python 3, any :class:`str`
            that is written to the file will be converted to
            :class:`bytes`.

        :Parameters:
          - `root_collection`: A :class:`MotorCollection`, the root collection
             to write to
          - `**kwargs` (optional): file level options (see above)
        """
        if isinstance(root_collection, grid_file.GridIn):
            # Short cut
            MotorOpenable.__init__(
                self, root_collection, kwargs.pop('io_loop', None))
        else:
            if not isinstance(root_collection, MotorCollection):
                raise TypeError(
                    "First argument to MotorGridIn must be "
                    "MotorCollection, not %r" % root_collection)

            assert 'io_loop' not in kwargs, \
                "Can't override IOLoop for MotorGridIn"
            MotorOpenable.__init__(
                self, None, root_collection.get_io_loop(),
                root_collection.delegate, **kwargs)

MotorGridIn.set = asynchronize(
    MotorGridIn, gridfs.GridIn.__setattr__, False, doc="""
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
""")


class MotorGridFS(MotorOpenable):
    __delegate_class__ = gridfs.GridFS

    new_file            = AsyncRead().wrap(grid_file.GridIn)
    get                 = AsyncRead().wrap(grid_file.GridOut)
    get_version         = AsyncRead().wrap(grid_file.GridOut)
    get_last_version    = AsyncRead().wrap(grid_file.GridOut)
    list                = AsyncRead()
    exists              = AsyncRead()
    put                 = AsyncCommand()
    delete              = AsyncCommand()

    def __init__(self, database, collection="fs"):
        """
        An instance of GridFS on top of a single Database. You must call
        :meth:`open` before using the `MotorGridFS` object.

        :Parameters:
          - `database`: a :class:`MotorDatabase`
          - `collection` (optional): A string, name of root collection to use,
            such as "fs" or "my_files"

        .. mongodoc:: gridfs
        """
        if not isinstance(database, MotorDatabase):
            raise TypeError("First argument to MotorGridFS must be "
                            "MotorDatabase, not %r" % database)

        MotorOpenable.__init__(
            self, None, database.get_io_loop(), database.delegate, collection)

    def wrap(self, obj):
        if obj.__class__ is grid_file.GridIn:
            return MotorGridIn(obj, io_loop=self.get_io_loop())
        elif obj.__class__ is grid_file.GridOut:
            return MotorGridOut(obj, io_loop=self.get_io_loop())


def Op(fn, *args, **kwargs):
    """TODO: update docs, raise DeprecationWarning
    """
    result = fn(*args, **kwargs)
    assert isinstance(result, Future)  # TODO: remove?
    return result
