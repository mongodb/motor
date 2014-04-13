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

from __future__ import print_function, unicode_literals

"""Help test MotorReplicaSetClient and read preferences.

Motor's version of some replica set testing functions in PyMongo's test.utils.
"""

from tornado import gen
from pymongo.errors import AutoReconnect


@gen.coroutine
def read_from_which_host(
        rsc, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Read from a MongoReplicaSetClient with the given Read Preference mode,
       tags, and acceptable latency. Return the 'host:port' which was read from.

    :Parameters:
      - `rsc`: A MongoReplicaSetClient
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
    """
    db = rsc.motor_test
    db.read_preference = mode
    if isinstance(tag_sets, dict):
        tag_sets = [tag_sets]
    db.tag_sets = tag_sets or [{}]
    db.secondary_acceptable_latency_ms = secondary_acceptable_latency_ms

    cursor = db.test.find()
    try:
        yield cursor.fetch_next
        host = cursor.delegate._Cursor__connection_id
    except AutoReconnect:
        host = None

    raise gen.Return(host)


@gen.coroutine
def assert_read_from(
        testcase, rsc, member, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Check that a query with the given mode, tag_sets, and
       secondary_acceptable_latency_ms reads from the expected replica-set
       member

    :Parameters:
      - `testcase`: A unittest.TestCase
      - `rsc`: A MongoReplicaSetClient
      - `member`: Member expected to be used
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
      - `callback`: Function taking (None, error)
    """
    nsamples = 10
    used = yield [
        read_from_which_host(
            rsc, mode, tag_sets, secondary_acceptable_latency_ms)
        for _ in range(nsamples)
    ]

    testcase.assertEqual([member] * nsamples, used)


@gen.coroutine
def assert_read_from_all(
        testcase, rsc, members, mode,
        tag_sets=None, secondary_acceptable_latency_ms=15):
    """Check that a query with the given mode, tag_sets, and
    secondary_acceptable_latency_ms reads from all members in a set, and
    only members in that set.

    :Parameters:
      - `testcase`: A unittest.TestCase
      - `rsc`: A MotorReplicaSetClient
      - `members`: Sequence of expected host:port to be used
      - `mode`: A ReadPreference
      - `tag_sets` (optional): List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms` (optional): a float
      - `callback`: Function taking (None, error)
    """
    nsamples = 100
    members = set(members)
    used = set((yield [
        read_from_which_host(
            rsc, mode, tag_sets, secondary_acceptable_latency_ms)
        for _ in range(nsamples)
    ]))

    testcase.assertEqual(members, used)
