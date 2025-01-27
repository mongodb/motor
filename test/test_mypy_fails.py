import os
import sys
import unittest
from typing import Iterable

try:
    from mypy import api
except ImportError:
    api = None

sys.path[0:0] = [""]


TEST_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "mypy_fails")


def get_tests() -> Iterable[str]:
    for dirpath, _, filenames in os.walk(TEST_PATH):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


class TestMypyFails(unittest.TestCase):
    def ensure_mypy_fails(self, filename: str) -> None:
        if api is None:
            raise unittest.SkipTest("Mypy is not installed")
        stdout, stderr, exit_status = api.run([filename])
        self.assertTrue(exit_status, msg=stdout)

    def test_mypy_failures(self) -> None:
        for filename in get_tests():
            with self.subTest(filename=filename):
                self.ensure_mypy_fails(filename)
