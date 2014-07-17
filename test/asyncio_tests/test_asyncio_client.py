# Copyright 2011-2014 MongoDB, Inc.
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

"""Test AsyncIOMotorClient."""

import unittest

from test.asyncio_tests import (asyncio_client_test_generic,
                                asyncio_test,
                                AsyncIOTestCase)


class TestAsyncIOClient(AsyncIOTestCase):
    @asyncio_test
    def test_client_open(self):
        cx = self.asyncio_client()
        self.assertEqual(cx, (yield from cx.open()))
        self.assertEqual(cx, (yield from cx.open()))  # Same the second time.


class AsyncIOClientTestGeneric(
        asyncio_client_test_generic.AsyncIOClientTestMixin,
        AsyncIOTestCase):

    def get_client(self, *args, **kwargs):
        return self.asyncio_client(*args, **kwargs)


if __name__ == '__main__':
    unittest.main()
