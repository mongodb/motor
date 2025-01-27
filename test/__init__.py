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

from test.test_environment import CLIENT_PEM, db_user, env  # noqa: F401
from typing import Any
from unittest import SkipTest  # noqa: F401

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


class MockRequestHandler:
    """For testing MotorGridOut.stream_to_handler."""

    def __init__(self) -> None:
        self.n_written = 0

    def write(self, data: Any) -> None:
        self.n_written += len(data)

    def flush(self) -> None:
        pass
