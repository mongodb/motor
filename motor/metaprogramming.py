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

"""Dynamic class-creation for Motor."""

import inspect
import functools

import greenlet
from pymongo.cursor import Cursor

from . import motor_py3_compat
from .motor_common import (callback_type_error,
                           check_deprecated_kwargs,
                           mangle_delegate_name)

_class_cache = {}


def asynchronize(
        motor_class,
        framework,
        sync_method,
        has_write_concern,
        doc=None):
    """Decorate `sync_method` so it accepts a callback or returns a Future.

    The method runs on a child greenlet and calls the callback or resolves
    the Future when the greenlet completes.

    :Parameters:
     - `motor_class`:       Motor class being created, e.g. MotorClient.
     - `framework`:         An asynchronous framework
     - `sync_method`:       Unbound method of pymongo Collection, Database,
                            MongoClient, etc.
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
            future = framework.get_future(self.get_io_loop())

        def call_method():
            # Runs on child greenlet.
            try:
                result = sync_method(self.delegate, *args, **kwargs)
                if callback:
                    # Schedule callback(result, None) on main greenlet.
                    framework.call_soon(
                        loop,
                        functools.partial(callback, result, None))
                else:
                    # Schedule future to be resolved on main greenlet.
                    framework.call_soon(
                        loop,
                        functools.partial(future.set_result, result))
            except Exception as e:
                if callback:
                    framework.call_soon(
                        loop,
                        functools.partial(callback, None, e))
                else:
                    # TODO: we lost Tornado's set_exc_info. Frameworkify this.
                    framework.call_soon(
                        loop,
                        functools.partial(future.set_exception, e))

        # Start running the operation on a greenlet.
        greenlet.greenlet(call_method).switch()
        return future

    # This is for the benefit of motor_extensions.py, which needs this info to
    # generate documentation with Sphinx.
    method.is_async_method = True
    method.has_write_concern = has_write_concern
    name = sync_method.__name__
    method.pymongo_method_name = mangle_delegate_name(motor_class, name)
    if doc is not None:
        method.__doc__ = doc

    return method


_coro_token = object()


def motor_coroutine(f):
    """Used by Motor classes to mark functions as coroutines.

    create_class_with_framework will decorate the function with a framework-
    specific coroutine decorator, like asyncio.coroutine or Tornado's
    gen.coroutine.

    You cannot return a value from a motor_coroutine, the syntax differences
    between Tornado on Python 2 and asyncio with Python 3.5 are impossible to
    bridge.
    """
    f._is_motor_coroutine = _coro_token
    return f


class MotorAttributeFactory(object):
    # TODO: update.
    """Used by Motor classes to mark attributes that delegate in some way to
    PyMongo. At module import time, each Motor class is created, and MotorMeta
    calls create_attribute() for each attr to create the final class attribute.
    """
    def __init__(self, doc=None):
        self.doc = doc

    def create_attribute(self, cls, attr_name):
        raise NotImplementedError


class Async(MotorAttributeFactory):
    def __init__(self, attr_name, has_write_concern, doc=None):
        """A descriptor that wraps a PyMongo method, such as insert or remove,
        and returns an asynchronous version of the method, which accepts a
        callback or returns a Future.

        :Parameters:
         - `attr_name`: The name of the attribute on the PyMongo class, if
           different from attribute on the Motor class
         - `has_write_concern`: Whether the method accepts getLastError options
        """
        super(Async, self).__init__(doc)
        self.attr_name = attr_name
        self.has_write_concern = has_write_concern

    def create_attribute(self, cls, attr_name):
        name = mangle_delegate_name(cls, self.attr_name or attr_name)
        method = getattr(cls.__delegate_class__, name)
        return asynchronize(
            motor_class=cls,
            framework=cls._framework,
            sync_method=method,
            has_write_concern=self.has_write_concern,
            doc=self.doc)

    def wrap(self, original_class):
        return WrapAsync(self, original_class)

    def unwrap(self, class_name):
        return Unwrap(self, class_name)


class WrapBase(MotorAttributeFactory):
    def __init__(self, prop, doc=None):
        super(WrapBase, self).__init__(doc)
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
        - `original_class`: A PyMongo class to be wrapped.
        """
        super(WrapAsync, self).__init__(prop)
        self.original_class = original_class

    def create_attribute(self, cls, attr_name):
        async_method = self.property.create_attribute(cls, attr_name)
        original_class = self.original_class
        wrapper = cls._framework.pymongo_class_wrapper(async_method,
                                                       original_class)
        if self.doc:
            wrapper.__doc__ = self.doc

        return wrapper


class Unwrap(WrapBase):
    def __init__(self, prop, motor_class_name):
        """A descriptor that checks if arguments are Motor classes and unwraps
        them. E.g., Motor's drop_database takes a MotorDatabase, unwraps it,
        and passes a PyMongo Database instead.

        :Parameters:
        - `prop`: An Async, the async method to call with unwrapped arguments.
        - `motor_class_name`: Like 'MotorDatabase' or 'MotorCollection'.
        """
        super(Unwrap, self).__init__(prop)
        assert isinstance(motor_class_name, motor_py3_compat.text_type)
        self.motor_class_name = motor_class_name

    def create_attribute(self, cls, attr_name):
        f = self.property.create_attribute(cls, attr_name)
        name = self.motor_class_name

        @functools.wraps(f)
        def _f(self, *args, **kwargs):
            # Don't call isinstance(), not checking subclasses.
            unwrapped_args = [
                obj.delegate if obj.__class__.__name__ == name else obj
                for obj in args]

            unwrapped_kwargs = dict([
                (key, obj.delegate if obj.__class__.__name__ == name else obj)
                for key, obj in kwargs.items()])

            return f(self, *unwrapped_args, **unwrapped_kwargs)

        if self.doc:
            _f.__doc__ = self.doc

        return _f


class AsyncRead(Async):
    def __init__(self, attr_name=None, doc=None):
        """A descriptor that wraps a PyMongo read method like find_one() that
        returns a Future.
        """
        Async.__init__(
            self, attr_name=attr_name, has_write_concern=False, doc=doc)


class AsyncWrite(Async):
    def __init__(self, attr_name=None, doc=None):
        """A descriptor that wraps a PyMongo write method like update() that
        accepts getLastError options and returns a Future.
        """
        Async.__init__(
            self, attr_name=attr_name, has_write_concern=True, doc=doc)


class AsyncCommand(Async):
    def __init__(self, attr_name=None, doc=None):
        """A descriptor that wraps a PyMongo command like copy_database() that
        returns a Future and does not accept getLastError options.
        """
        Async.__init__(
            self, attr_name=attr_name, has_write_concern=False, doc=doc)


class ReadOnlyPropertyDescriptor(object):
    def __init__(self, attr_name, doc=None):
        self.attr_name = attr_name
        if doc:
            self.__doc__ = doc

    def __get__(self, obj, objtype):
        if obj:
            return getattr(obj.delegate, self.attr_name)
        else:
            # We're accessing this property on a class, e.g. when Sphinx wants
            # MotorClient.read_preference.__doc__.
            return getattr(objtype.__delegate_class__, self.attr_name)

    def __set__(self, obj, val):
        raise AttributeError


class ReadOnlyProperty(MotorAttributeFactory):
    """Creates a readonly attribute on the wrapped PyMongo object"""
    def create_attribute(self, cls, attr_name):
        return ReadOnlyPropertyDescriptor(attr_name, self.doc)


class DelegateMethod(ReadOnlyProperty):
    """A method on the wrapped PyMongo object that does no I/O and can be called
    synchronously"""


class ReadWritePropertyDescriptor(ReadOnlyPropertyDescriptor):
    def __set__(self, obj, val):
        setattr(obj.delegate, self.attr_name, val)


class ReadWriteProperty(MotorAttributeFactory):
    """Creates a mutable attribute on the wrapped PyMongo object"""
    def create_attribute(self, cls, attr_name):
        return ReadWritePropertyDescriptor(attr_name, self.doc)


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
        if self.doc:
            return_clone.__doc__ = self.doc

        return return_clone


def create_class_with_framework(cls, framework, module_name):
    motor_class_name = cls.__motor_class_name__
    cache_key = (cls, motor_class_name, framework)
    cached_class = _class_cache.get(cache_key)
    if cached_class:
        return cached_class

    new_class = type(str(motor_class_name), cls.__bases__, cls.__dict__.copy())
    new_class.__module__ = module_name
    new_class._framework = framework

    assert hasattr(new_class, '__delegate_class__')

    # If we're constructing MotorClient from AgnosticClient, for example,
    # the method resolution order is (AgnosticClient, AgnosticBase, object).
    # Iterate over bases looking for attributes and coroutines that must be
    # replaced with framework-specific ones.
    for base in reversed(inspect.getmro(cls)):
        # Turn attribute factories into real methods or descriptors.
        for name, attr in base.__dict__.items():
            if isinstance(attr, MotorAttributeFactory):
                new_class_attr = attr.create_attribute(new_class, name)
                setattr(new_class, name, new_class_attr)

            elif getattr(attr, '_is_motor_coroutine', None) is _coro_token:
                coro = framework.coroutine(attr)
                del coro._is_motor_coroutine
                setattr(new_class, name, coro)

    _class_cache[cache_key] = new_class
    return new_class
