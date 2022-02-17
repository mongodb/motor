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

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import logging
import unittest
from test.test_environment import CLIENT_PEM, db_user, env  # noqa: F401
from unittest import SkipTest

try:
    # Enable the fault handler to dump the traceback of each running
    # thread
    # after a segfault.
    import faulthandler

    faulthandler.enable()
    # Dump the tracebacks of all threads after 25 minutes.
    if hasattr(faulthandler, "dump_traceback_later"):
        faulthandler.dump_traceback_later(25 * 60)
except ImportError:
    pass


def suppress_tornado_warnings():
    for name in ["tornado.general", "tornado.access"]:
        logger = logging.getLogger(name)
        logger.setLevel(logging.ERROR)


class SkippedModule(object):
    def __init__(self, name, reason):
        def runTest(self):
            raise SkipTest(str(reason))

        self.test_case = type(str(name), (unittest.TestCase,), {"runTest": runTest})


class MotorTestLoader(unittest.TestLoader):
    def __init__(self, avoid=None, reason=None):
        super().__init__()
        self._avoid = []

    def avoid(self, *prefixes, **kwargs):
        """Skip a module.

        The usual "raise SkipTest" from a module doesn't work if the module
        won't even parse in Python 2, so prevent TestLoader from importing
        modules with the given prefix.

        "prefix" is a path prefix like "asyncio_tests".
        """
        for prefix in prefixes:
            self._avoid.append((prefix, kwargs["reason"]))

    def _get_module_from_name(self, name):
        for prefix, reason in self._avoid:
            if name.startswith(prefix):
                return SkippedModule(name, reason)

        return super()._get_module_from_name(name)


class MockRequestHandler(object):
    """For testing MotorGridOut.stream_to_handler."""

    def __init__(self):
        self.n_written = 0

    def write(self, data):
        self.n_written += len(data)

    def flush(self):
        pass
