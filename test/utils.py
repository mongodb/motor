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

from collections import defaultdict

from pymongo import monitoring

"""Utilities for testing Motor with any framework."""

import contextlib
import functools
import warnings


def one(s):
    """Get one element of a set"""
    return next(iter(s))


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


def get_primary_pool(client):
    for s in client.delegate._topology._servers.values():
        if s.description.is_writable:
            return s.pool


# Ignore auth commands like saslStart, so we can assert lsid is in all commands.
class SessionTestListener(monitoring.CommandListener):
    def __init__(self):
        self.results = defaultdict(list)

    def started(self, event):
        if not event.command_name.startswith('sasl'):
            self.results['started'].append(event)

    def succeeded(self, event):
        if not event.command_name.startswith('sasl'):
            self.results['succeeded'].append(event)

    def failed(self, event):
        if not event.command_name.startswith('sasl'):
            self.results['failed'].append(event)

    def first_command_started(self):
        assert len(self.results['started']) >= 1, (
            "No command-started events")

        return self.results['started'][0]


def session_ids(client):
    return [s.session_id for s in client.delegate._topology._session_pool]
