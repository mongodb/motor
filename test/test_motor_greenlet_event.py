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

"""Test MotorGreenletEvent."""
import greenlet
from functools import partial

from tornado import testing, gen
from tornado.testing import gen_test

from motor.util import MotorGreenletEvent


class MotorTestEvent(testing.AsyncTestCase):
    @gen.coroutine
    def tick(self):
        # Yield to loop for one iteration.
        yield gen.Task(self.io_loop.add_callback)

    @gen_test
    def test_event_basic(self):
        event = MotorGreenletEvent(self.io_loop)
        self.assertFalse(event.is_set())

        waiter = greenlet.greenlet(event.wait)
        waiter.switch()
        yield self.tick()
        self.assertTrue(waiter)     # Blocked: not finished yet.
        event.set()
        yield self.tick()
        self.assertFalse(waiter)    # Complete.

        self.assertTrue(event.is_set())

    @gen_test
    def test_event_multi(self):
        # Two greenlets are run, FIFO, after being unblocked.
        event = MotorGreenletEvent(self.io_loop)
        order = []

        def wait():
            event.wait()
            order.append(greenlet.getcurrent())

        waiter0 = greenlet.greenlet(wait)
        waiter1 = greenlet.greenlet(wait)
        waiter0.switch()
        waiter1.switch()
        event.set()
        yield self.tick()
        self.assertEqual([waiter0, waiter1], order)

    @gen_test
    def test_event_timeout(self):
        event = MotorGreenletEvent(self.io_loop)
        waiter = greenlet.greenlet(partial(event.wait, timeout_seconds=0))
        waiter.switch()
        yield self.tick()
        self.assertFalse(waiter)  # Unblocked, finished.
