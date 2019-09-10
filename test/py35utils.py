# Copyright 2019-present MongoDB, Inc.
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

import time

"""Utilities for testing Motor on Python 3.5+."""


async def wait_until(predicate, success_description, timeout=10):
    """Copied from PyMongo's test.utils.wait_until.

    Wait up to 10 seconds (by default) for predicate to be true. The
    predicate must be an awaitable.

    Returns the predicate's first true value.
    """
    start = time.time()
    interval = min(float(timeout)/100, 0.1)
    while True:
        retval = await predicate()
        if retval:
            return retval

        if time.time() - start > timeout:
            raise AssertionError("Didn't ever %s" % success_description)

        time.sleep(interval)
