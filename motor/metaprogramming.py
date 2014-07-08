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


_class_cache = {}


def create_class_with_framework(cls, framework):
    motor_class_name = cls.__motor_class_name__
    key = (cls, motor_class_name, framework)
    cached_class = _class_cache.get(key)
    if cached_class:
        return cached_class

    new_class = type(str(motor_class_name), cls.__bases__, cls.__dict__.copy())

    # TODO: pass to create_attribute instead of setting here?
    new_class._framework = framework

    # TODO: move attribute factories to this file
    from .core import MotorAttributeFactory

    # TODO: can't happen any more? assert has __delegate_class__
    # If new_class has no __delegate_class__, then it's a base like
    # AgnosticClientBase; don't try to update its attrs, we'll use them
    # for its subclasses like MotorClient.
    if getattr(new_class, '__delegate_class__', None):
        for base in reversed(inspect.getmro(new_class)):
            # Turn attribute factories into real methods or descriptors.
            for motor_class_name, attr in base.__dict__.items():
                if isinstance(attr, MotorAttributeFactory):
                    new_class_attr = attr.create_attribute(
                        new_class, motor_class_name)

                    setattr(new_class, motor_class_name, new_class_attr)

    _class_cache[key] = new_class
    return new_class
