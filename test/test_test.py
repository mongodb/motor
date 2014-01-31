# Copyright 2013-2014 MongoDB, Inc.
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

"""Test Motor's test helpers."""

from tornado.concurrent import Future
from tornado.testing import gen_test

from motor import callback_type_error
from test import MotorTest, assert_raises


# Example function to be tested, helps verify that check_optional_callback
# works.
def require_callback(callback=None):
    if not callable(callback):
        raise callback_type_error
    callback(None, None)


def dont_require_callback(callback=None):
    if callback:
        if not callable(callback):
            raise callback_type_error

        callback(None, None)
    else:
        future = Future()
        future.set_result(None)
        return future


class MotorCallbackTestTest(MotorTest):
    @gen_test
    def test_check_optional_callback(self):
        yield self.check_optional_callback(dont_require_callback)
        with assert_raises(Exception):
            yield self.check_optional_callback(require_callback)
