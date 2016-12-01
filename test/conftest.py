# If you choose to run Motor's tests with py.test, this is its config.

import pytest

from test import env


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    env.setup()
