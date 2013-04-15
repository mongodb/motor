# Copyright 2012 10gen, Inc.
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

import threading
import time
import unittest

from tornado import gen
from tornado.ioloop import IOLoop

from test import host, port, MotorTest, async_test_engine


class MotorTailTest(MotorTest):
    def setUp(self):
        super(MotorTailTest, self).setUp()
        self.sync_db.capped.drop()
        # autoIndexId catches test bugs that try to insert duplicate _id's
        self.sync_db.create_collection(
            'capped', capped=True, size=1000, autoIndexId=True)

        self.sync_db.uncapped.drop()
        self.sync_db.uncapped.insert({})

    def start_insertion_thread(self, pauses):
        """A thread that gradually inserts documents into a capped collection
        """
        def add_docs():
            i = 0
            for pause in pauses:
                if pause == 'drop':
                    self.sync_db.capped.drop()
                else:
                    time.sleep(pause)
                    self.sync_db.capped.insert({'_id': i})
                    i += 1

        t = threading.Thread(target=add_docs)
        t.start()
        return t

    # Need at least one pause > 4.5 seconds to ensure we recover when
    # getMore times out
    tail_pauses = (0, 1, 0, 1, 0, 5, 0, 0)

    @async_test_engine(timeout_sec=sum(tail_pauses) + 30)
    def test_tail(self, done):
        expected = [{'_id': i} for i in range(len(self.tail_pauses))]
        t = self.start_insertion_thread(self.tail_pauses)
        test_db = self.motor_client(host, port).pymongo_test
        capped = test_db.capped

        cursor = capped.find(tailable=True, await_data=True)
        results = []
        while results != expected:
            print 'restart'
            while (yield cursor.fetch_next):
                doc = cursor.next_object()
                print doc
                results.append(doc)

        t.join()

        # Clear cursor from this scope and from Runner
        cursor = None
        yield gen.Task(IOLoop.instance().add_callback)
        yield gen.Task(self.wait_for_cursors)
        done()


if __name__ == '__main__':
    unittest.main()
