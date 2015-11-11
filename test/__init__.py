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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import logging

try:
    # Python 2.6.
    from unittest2 import SkipTest
    import unittest2 as unittest
except ImportError:
    from unittest import SkipTest  # If this fails you need unittest2.
    import unittest

from test.test_environment import env, db_user, CLIENT_PEM


def suppress_tornado_warnings():
    for name in [
            'tornado.general',
            'tornado.access']:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)


class SkippedModule(object):
    def __init__(self, name, reason):
        def runTest(self):
            raise SkipTest(str(reason))

        self.test_case = type(
            str(name),
            (unittest.TestCase, ),
            {'runTest': runTest})


class MotorTestLoader(unittest.TestLoader):
    def __init__(self, avoid=None, reason=None):
        super(MotorTestLoader, self).__init__()
        self._avoid = []

    def avoid(self, prefix, reason):
        """Skip a module.

        The usual "raise SkipTest" from a module doesn't work if the module
        won't even parse in Python 2, so prevent TestLoader from importing
        modules with the given prefix.

        "prefix" is a path prefix like "asyncio_tests".
        """
        self._avoid.append((prefix, reason))

    def _get_module_from_name(self, name):
        for prefix, reason in self._avoid:
            if name.startswith(prefix):
                # By experiment, need two tactics to work in unittest2 & stdlib.
                if unittest.__name__ == 'unittest2':
                    raise SkipTest(reason)
                else:
                    return SkippedModule(name, reason)

        return super(MotorTestLoader, self)._get_module_from_name(name)


class MotorTestRunner(unittest.TextTestRunner):
    """Runs suite-level setup and teardown."""
    def __init__(self, *args, **kwargs):
        self.tornado_warnings = kwargs.pop('tornado_warnings', False)
        super(MotorTestRunner, self).__init__(*args, **kwargs)

    def run(self, test):
        env.setup()
        if not self.tornado_warnings:
            suppress_tornado_warnings()

        result = super(MotorTestRunner, self).run(test)
        env.teardown()
        return result


class MockRequestHandler(object):
    """For testing MotorGridOut.stream_to_handler."""
    def __init__(self):
        self.n_written = 0

    def write(self, data):
        self.n_written += len(data)

    def flush(self):
        pass
