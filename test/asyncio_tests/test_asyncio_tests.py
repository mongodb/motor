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

"""Test Motor's asyncio test utilities."""

import asyncio
import io
import unittest


from test.asyncio_tests import AsyncIOTestCase, asyncio_test


def run_test_case(case):
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(case)
    runner = unittest.TextTestRunner(stream=io.StringIO())
    return runner.run(suite)


class TestAsyncIOTests(unittest.TestCase):
    def test_basic(self):
        class Test(AsyncIOTestCase):
            @asyncio_test
            def test(self):
                pass

        result = run_test_case(Test)
        self.assertEqual(1, result.testsRun)
        self.assertEqual(0, len(result.errors))

    def test_timeout(self):
        class Test(AsyncIOTestCase):
            @asyncio_test(timeout=0.01)
            def test_that_is_too_slow(self):
                yield from self.middle()

            @asyncio.coroutine
            def middle(self):
                yield from self.inner()

            @asyncio.coroutine
            def inner(self):
                yield from asyncio.sleep(1, loop=self.loop)

        result = run_test_case(Test)
        self.assertEqual(1, len(result.errors))
        case, text = result.errors[0]
        self.assertTrue('CancelledError' in text)
        self.assertTrue('timed out after 0.01 seconds' in text)

        # The traceback shows where the coroutine hung.
        self.assertTrue('test_that_is_too_slow' in text)
        self.assertTrue('middle' in text)
        self.assertTrue('inner' in text)

    def test_failure(self):
        class Test(AsyncIOTestCase):
            @asyncio_test
            def test_that_fails(self):
                yield from self.middle()

            @asyncio.coroutine
            def middle(self):
                yield from self.inner()

            @asyncio.coroutine
            def inner(self):
                assert False, 'expected error'

        result = run_test_case(Test)
        self.assertEqual(1, len(result.failures))
        case, text = result.failures[0]
        self.assertFalse('CancelledError' in text)
        self.assertTrue('AssertionError' in text)
        self.assertTrue('expected error' in text)

        # The traceback shows where the coroutine raised.
        self.assertTrue('test_that_fails' in text)
        self.assertTrue('middle' in text)
        self.assertTrue('inner' in text)

if __name__ == '__main__':
    unittest.main()
