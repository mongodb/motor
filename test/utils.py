# Copyright 2012-2015 MongoDB, Inc.
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

from __future__ import unicode_literals

"""Utilities for testing Motor with any framework."""

import contextlib
import functools
import warnings


def one(s):
    """Get one element of a set"""
    return next(iter(s))


def delay(sec):
    # Javascript sleep() available in MongoDB since version ~1.9
    return 'sleep(%s * 1000); return true' % sec


def safe_get(dct, dotted_key, default=None):
    for key in dotted_key.split('.'):
        if key not in dct:
            return default

        dct = dct[key]

    return dct


# Use as a decorator or in a "with" statement.
def ignore_deprecations(fn=None):
    if fn:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                return fn(*args, **kwargs)

        return wrapper

    else:
        @contextlib.contextmanager
        def ignore_deprecations_context():
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                yield

        return ignore_deprecations_context()
