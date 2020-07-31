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

from collections import defaultdict

from bson import SON
from pymongo import monitoring

"""Utilities for testing Motor with any framework."""

import contextlib
import functools
import os
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
class TestListener(monitoring.CommandListener):
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

    def first_command_started(self, name=None):
        assert len(self.results['started']) >= 1, (
            "No command-started events")

        if name:
            for result in self.results['started']:
                if result.command_name == name:
                    return result
        else:
            return self.results['started'][0]

    def started_command_names(self):
        """Return list of command names started."""
        return [event.command_name for event in self.results['started']]


def session_ids(client):
    return [s.session_id for s in client.delegate._topology._session_pool]


def create_user(authdb, user, pwd=None, roles=None, **kwargs):
    cmd = SON([('createUser', user)])
    # X509 doesn't use a password
    if pwd:
        cmd['pwd'] = pwd
    cmd['roles'] = roles or ['root']
    cmd.update(**kwargs)
    return authdb.command(cmd)


def get_async_test_timeout(default=5):
    """Get the global timeout setting for async tests.

    Returns a float, the timeout in seconds.
    """
    try:
        timeout = float(os.environ.get('ASYNC_TEST_TIMEOUT'))
        return max(timeout, default)
    except (ValueError, TypeError):
        return default


class FailPoint:
    def __init__(self, client, command_args):
        self.client = client
        self.cmd_on = SON([('configureFailPoint', 'failCommand')])
        self.cmd_on.update(command_args)

    async def __aenter__(self):
        await self.client.admin.command(self.cmd_on)

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.admin.command(
            'configureFailPoint', self.cmd_on['configureFailPoint'],
            mode='off')
