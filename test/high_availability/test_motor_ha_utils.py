# Copyright 2013 10gen, Inc.
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

"""Help test MotorReplicaSetClient and read preferences.

Motor's version of some replica set testing functions in PyMongo's test.utils.
"""

from tornado import gen
from pymongo.errors import AutoReconnect


@gen.engine
def read_from_which_host(
    rsc, mode,
    tag_sets=None, secondary_acceptable_latency_ms=15, callback=None,
):
    """Read from a ReplicaSetConnection with the given Read Preference mode,
       tags, and acceptable latency. Return the 'host:port' which was read from.

    :Parameters:
      - `rsc`: A ReplicaSetConnection
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
      - `callback`: Function taking host:port or None
    """
    db = rsc.pymongo_test
    db.read_preference = mode
    if isinstance(tag_sets, dict):
        tag_sets = [tag_sets]
    db.tag_sets = tag_sets or [{}]
    db.secondary_acceptable_latency_ms = secondary_acceptable_latency_ms

    cursor = db.test.find()
    try:
        yield cursor.fetch_next
        callback(cursor.delegate._Cursor__connection_id)
    except AutoReconnect:
        callback(None)


@gen.engine
def assertReadFrom(
    testcase, rsc, member, mode,
    tag_sets=None, secondary_acceptable_latency_ms=15, callback=None
):
    """Check that a query with the given mode, tag_sets, and
       secondary_acceptable_latency_ms reads from the expected replica-set
       member

    :Parameters:
      - `testcase`: A unittest.TestCase
      - `rsc`: A ReplicaSetConnection
      - `member`: replica_set_connection.Member expected to be used
      - `mode`: A ReadPreference
      - `tag_sets`: List of dicts of tags for data-center-aware reads
      - `secondary_acceptable_latency_ms`: a float
      - `callback`: Function taking (None, error)
    """
    nsamples = 10
    try:
        for i in range(nsamples):
            read_from_which_host(
                rsc, mode, tag_sets, secondary_acceptable_latency_ms,
                callback=(yield gen.Callback(i)))

        used = yield gen.WaitAll(range(nsamples))
        testcase.assertEqual([member] * nsamples, used)
    except Exception, e:
        callback(None, e)
    else:
        # Success
        callback(None, None)


@gen.engine
def assertReadFromAll(
    testcase, rsc, members, mode,
    tag_sets=None, secondary_acceptable_latency_ms=15, callback=None
):
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

    for i in range(nsamples):
        read_from_which_host(
            rsc, mode, tag_sets, secondary_acceptable_latency_ms,
            callback=(yield gen.Callback(i)))

    used = set((yield gen.WaitAll(range(nsamples))))

    try:
        testcase.assertEqual(members, used)
    except Exception, e:
        callback(None, e)
    else:
        # Success
        callback(None, None)
