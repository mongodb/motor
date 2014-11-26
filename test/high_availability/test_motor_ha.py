# Copyright 2012-2014 MongoDB, Inc.
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

"""Test replica set operations and failures. A Motor version of PyMongo's
   test/high_availability/test_ha.py
"""

from __future__ import print_function, unicode_literals

import time
import unittest
from tornado import gen, testing

import pymongo
from pymongo import ReadPreference
from pymongo.mongo_replica_set_client import Member, Monitor, _partition_node
from pymongo.errors import AutoReconnect, OperationFailure
from tornado.testing import gen_test

import motor
import ha_tools
from test.utils import one
from test import assert_raises, PauseMixin, suppress_tornado_warnings
from test_motor_ha_utils import assert_read_from, assert_read_from_all


# Override default 30-second interval for faster testing
Monitor._refresh_interval = MONITOR_INTERVAL = 0.5


# To make the code terser, copy modes into module scope
PRIMARY = ReadPreference.PRIMARY
PRIMARY_PREFERRED = ReadPreference.PRIMARY_PREFERRED
SECONDARY = ReadPreference.SECONDARY
SECONDARY_PREFERRED = ReadPreference.SECONDARY_PREFERRED
NEAREST = ReadPreference.NEAREST


class MotorHATestCase(PauseMixin, testing.AsyncTestCase):
    """A test case for Motor connections to replica sets or mongos."""

    def tearDown(self):
        ha_tools.kill_all_members()
        ha_tools.nodes.clear()
        ha_tools.routers.clear()
        time.sleep(1)  # Let members really die.


class MotorTestDirectConnection(MotorHATestCase):
    def setUp(self):
        super(MotorTestDirectConnection, self).setUp()
        members = [{}, {}, {'arbiterOnly': True}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res
        self.c = None

    @gen_test
    def test_secondary_connection(self):
        self.c = yield motor.MotorReplicaSetClient(
            self.seed, replicaSet=self.name).open()

        self.assertTrue(bool(len(self.c.secondaries)))
        db = self.c.motor_test
        yield db.test.remove({}, w=len(self.c.secondaries))

        # Wait for replication...
        w = len(self.c.secondaries) + 1
        yield db.test.insert({'foo': 'bar'}, w=w)

        # Test direct connection to a primary or secondary
        primary_host, primary_port = ha_tools.get_primary().split(':')
        primary_port = int(primary_port)
        (secondary_host,
         secondary_port) = ha_tools.get_secondaries()[0].split(':')
        secondary_port = int(secondary_port)
        arbiter_host, arbiter_port = ha_tools.get_arbiters()[0].split(':')
        arbiter_port = int(arbiter_port)

        # A connection succeeds no matter the read preference
        for kwargs in [
            {'read_preference': PRIMARY},
            {'read_preference': PRIMARY_PREFERRED},
            {'read_preference': SECONDARY},
            {'read_preference': SECONDARY_PREFERRED},
            {'read_preference': NEAREST},
        ]:
            client = yield motor.MotorClient(
                primary_host, primary_port, **kwargs).open()

            self.assertEqual(primary_host, client.host)
            self.assertEqual(primary_port, client.port)
            self.assertTrue(client.is_primary)

            # Direct connection to primary can be queried with any read pref
            self.assertTrue((yield client.motor_test.test.find_one()))

            client = yield motor.MotorClient(
                secondary_host, secondary_port, **kwargs).open()
            self.assertEqual(secondary_host, client.host)
            self.assertEqual(secondary_port, client.port)
            self.assertFalse(client.is_primary)

            # Direct connection to secondary can be queried with any read pref
            # but PRIMARY
            if kwargs.get('read_preference') != PRIMARY:
                self.assertTrue((
                    yield client.motor_test.test.find_one()))
            else:
                with assert_raises(AutoReconnect):
                    yield client.motor_test.test.find_one()

            # Since an attempt at an acknowledged write to a secondary from a
            # direct connection raises AutoReconnect('not master'), MotorClient
            # should do the same for unacknowledged writes.
            try:
                yield client.motor_test.test.insert({}, w=0)
            except AutoReconnect as e:
                self.assertEqual('not master', e.args[0])
            else:
                self.fail(
                    'Unacknowledged insert into secondary client %s should'
                    'have raised exception' % client)

            # Test direct connection to an arbiter
            client = yield motor.MotorClient(
                arbiter_host, arbiter_port, **kwargs).open()

            self.assertEqual(arbiter_host, client.host)
            self.assertEqual(arbiter_port, client.port)
            self.assertFalse(client.is_primary)

            # See explanation above
            try:
                yield client.motor_test.test.insert({}, w=0)
            except AutoReconnect as e:
                self.assertEqual('not master', e.args[0])
            else:
                self.fail(
                    'Unacknowledged insert into arbiter connection %s should'
                    'have raised exception' % client)

    def tearDown(self):
        self.c.close()
        super(MotorTestDirectConnection, self).tearDown()


class MotorTestPassiveAndHidden(MotorHATestCase):
    def setUp(self):
        super(MotorTestPassiveAndHidden, self).setUp()
        members = [
            {},
            {'priority': 0},
            {'arbiterOnly': True},
            {'priority': 0, 'hidden': True},
            {'priority': 0, 'slaveDelay': 5}]

        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

    @gen_test
    def test_passive_and_hidden(self):
        self.c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield self.c.open()

        passives = ha_tools.get_passives()
        passives = [_partition_node(member) for member in passives]
        self.assertEqual(self.c.secondaries, set(passives))

        for mode in SECONDARY, SECONDARY_PREFERRED:
            yield assert_read_from_all(self, self.c, passives, mode)

        ha_tools.kill_members(ha_tools.get_passives(), 2)
        yield self.pause(2 * MONITOR_INTERVAL)
        yield assert_read_from(
            self, self.c, self.c.primary, SECONDARY_PREFERRED)

    def tearDown(self):
        self.c.close()
        super(MotorTestPassiveAndHidden, self).tearDown()


class MotorTestMonitorRemovesRecoveringMember(MotorHATestCase):
    # Members in STARTUP2 or RECOVERING states are shown in the primary's
    # isMaster response, but aren't secondaries and shouldn't be read from.
    # Verify that if a secondary goes into RECOVERING mode, the Monitor removes
    # it from the set of readers.

    def setUp(self):
        super(MotorTestMonitorRemovesRecoveringMember, self).setUp()
        members = [{}, {'priority': 0}, {'priority': 0}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

    @gen_test
    def test_monitor_removes_recovering_member(self):
        self.c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield self.c.open()
        secondaries = ha_tools.get_secondaries()

        for mode in SECONDARY, SECONDARY_PREFERRED:
            partitioned_secondaries = [_partition_node(s) for s in secondaries]
            yield assert_read_from_all(
                self, self.c, partitioned_secondaries, mode)

        secondary, recovering_secondary = secondaries
        ha_tools.set_maintenance(recovering_secondary, True)
        yield self.pause(2 * MONITOR_INTERVAL)

        for mode in SECONDARY, SECONDARY_PREFERRED:
            # Don't read from recovering member
            yield assert_read_from(
                self, self.c, _partition_node(secondary), mode)

    def tearDown(self):
        self.c.close()
        super(MotorTestMonitorRemovesRecoveringMember, self).tearDown()


class MotorTestTriggeredRefresh(MotorHATestCase):
    # Verify that if a secondary goes into RECOVERING mode or if the primary
    # changes, the next exception triggers an immediate refresh.
    def setUp(self):
        super(MotorTestTriggeredRefresh, self).setUp()
        members = [{}, {}]
        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

        # Disable periodic refresh
        Monitor._refresh_interval = 1e6

    @gen_test(timeout=60)
    def test_recovering_member_triggers_refresh(self):
        # To test that find_one() and count() trigger immediate refreshes,
        # we'll create a separate client for each
        self.c_find_one, self.c_count = yield [
            motor.MotorReplicaSetClient(
                self.seed, replicaSet=self.name, read_preference=SECONDARY
            ).open() for _ in range(2)]

        # We've started the primary and one secondary
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_secondaries()[0]

        # Pre-condition: just make sure they all connected OK
        for c in self.c_find_one, self.c_count:
            self.assertEqual(one(c.secondaries), _partition_node(secondary))

        ha_tools.set_maintenance(secondary, True)

        # Trigger a refresh in various ways
        with assert_raises(AutoReconnect):
            yield self.c_find_one.test.test.find_one()

        with assert_raises(AutoReconnect):
            yield self.c_count.test.test.count()

        # Wait for the immediate refresh to complete - we're not waiting for
        # the periodic refresh, which has been disabled
        yield self.pause(1)

        for c in self.c_find_one, self.c_count:
            self.assertFalse(c.secondaries)
            self.assertEqual(_partition_node(primary), c.primary)

    @gen_test(timeout=60)
    def test_stepdown_triggers_refresh(self):
        c_find_one = yield motor.MotorReplicaSetClient(
            self.seed, replicaSet=self.name).open()

        # We've started the primary and one secondary
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_secondaries()[0]
        self.assertEqual(
            one(c_find_one.secondaries), _partition_node(secondary))

        ha_tools.stepdown_primary()

        # Make sure the stepdown completes
        yield self.pause(1)

        # Trigger a refresh
        with assert_raises(AutoReconnect):
            yield c_find_one.test.test.find_one()

        # Wait for the immediate refresh to complete - we're not waiting for
        # the periodic refresh, which has been disabled
        yield self.pause(1)

        # We've detected the stepdown
        self.assertTrue(
            not c_find_one.primary
            or primary != c_find_one.primary)

    def tearDown(self):
        Monitor._refresh_interval = MONITOR_INTERVAL
        super(MotorTestTriggeredRefresh, self).tearDown()


class MotorTestHealthMonitor(MotorHATestCase):
    def setUp(self):
        super(MotorTestHealthMonitor, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test(timeout=60)
    def test_primary_failure(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)
        primary = c.primary
        secondaries = c.secondaries
        killed = ha_tools.kill_primary()
        self.assertTrue(bool(len(killed)))
        yield self.pause(1)

        # Wait for new primary to step up, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(60):
            if c.primary != primary and c.secondaries != secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("New primary not detected")

    @gen_test(timeout=60)
    def test_secondary_failure(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)
        primary = c.primary

        killed = ha_tools.kill_secondary()
        self.assertTrue(bool(len(killed)))
        self.assertEqual(primary, c.primary)

        yield self.pause(2 * MONITOR_INTERVAL)
        secondaries = c.secondaries

        ha_tools.restart_members([killed])
        self.assertEqual(primary, c.primary)

        # Wait for secondary to join, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(30):
            if c.secondaries != secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("Dead secondary not detected")

    @gen_test(timeout=60)
    def test_primary_stepdown(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(bool(len(c.secondaries)))
        primary = c.primary
        secondaries = c.secondaries.copy()
        ha_tools.stepdown_primary()

        # Wait for primary to step down, and for MotorReplicaSetClient
        # to detect it.
        for _ in range(30):
            if c.primary != primary and secondaries != c.secondaries:
                break
            yield self.pause(1)
        else:
            self.fail("New primary not detected")


class MotorTestWritesWithFailover(MotorHATestCase):
    def setUp(self):
        super(MotorTestWritesWithFailover, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test(timeout=60)
    def test_writes_with_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        primary = c.primary
        db = c.motor_test
        w = len(c.secondaries) + 1
        yield db.test.remove(w=w)
        yield db.test.insert({'foo': 'bar'}, w=w)
        result = yield db.test.find_one()
        self.assertEqual('bar', result['foo'])

        killed = ha_tools.kill_primary(9)
        self.assertTrue(bool(len(killed)))
        yield self.pause(2)

        for _ in range(30):
            try:
                yield db.test.insert({'bar': 'baz'})

                # Success
                break
            except AutoReconnect:
                yield self.pause(1)
        else:
            self.fail("Couldn't insert after primary killed")

        self.assertTrue(primary != c.primary)
        result = yield db.test.find_one({'bar': 'baz'})
        self.assertEqual('baz', result['bar'])


class MotorTestReadWithFailover(MotorHATestCase):
    def setUp(self):
        super(MotorTestReadWithFailover, self).setUp()
        res = ha_tools.start_replica_set([{}, {}, {}])
        self.seed, self.name = res

    @gen_test(timeout=30)
    def test_read_with_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        self.assertTrue(c.secondaries)

        db = c.motor_test
        w = len(c.secondaries) + 1
        db.test.remove({}, w=w)
        # Force replication
        yield db.test.insert([{'foo': i} for i in range(10)], w=w)
        self.assertEqual(10, (yield db.test.count()))

        db.read_preference = SECONDARY
        cursor = db.test.find().batch_size(5)
        yield cursor.fetch_next
        self.assertEqual(5, cursor.delegate._Cursor__retrieved)
        for i in range(5):
            cursor.next_object()
        ha_tools.kill_primary()
        yield self.pause(2)

        # Primary failure shouldn't interrupt the cursor
        yield cursor.fetch_next
        self.assertEqual(10, cursor.delegate._Cursor__retrieved)


class MotorTestShipOfTheseus(MotorHATestCase):
    # If all of a replica set's members are replaced with new ones, is it still
    # the same replica set, or a different one?
    def setUp(self):
        super(MotorTestShipOfTheseus, self).setUp()
        res = ha_tools.start_replica_set([{}, {}])
        self.seed, self.name = res

    @gen_test(timeout=240)
    def test_ship_of_theseus(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        db = c.motor_test
        w = len(c.secondaries) + 1
        db.test.insert({}, w=w)

        primary = ha_tools.get_primary()
        secondary1 = ha_tools.get_random_secondary()
        ha_tools.add_member()
        ha_tools.add_member()
        ha_tools.add_member()

        # Wait for new members to join
        for _ in range(120):
            if ha_tools.get_primary() and len(ha_tools.get_secondaries()) == 4:
                break

            yield self.pause(1)
        else:
            self.fail("New secondaries didn't join")

        ha_tools.kill_members([primary, secondary1], 9)

        # Wait for primary
        for _ in range(30):
            if ha_tools.get_primary() and len(ha_tools.get_secondaries()) == 2:
                break

            yield self.pause(1)
        else:
            self.fail("No failover")

        # Ensure monitor picks up new members
        yield self.pause(2 * MONITOR_INTERVAL)

        try:
            yield db.test.find_one()
        except AutoReconnect:
            # Might take one try to reconnect
            yield self.pause(1)

        # No error
        yield db.test.find_one()
        yield db.test.find_one(read_preference=SECONDARY)


class MotorTestReadPreference(MotorHATestCase):
    def setUp(self):
        super(MotorTestReadPreference, self).setUp()
        members = [
            # primary
            {'tags': {'dc': 'ny', 'name': 'primary'}},

            # secondary
            {'tags': {'dc': 'la', 'name': 'secondary'}, 'priority': 0},

            # other_secondary
            {'tags': {'dc': 'ny', 'name': 'other_secondary'}, 'priority': 0},
        ]

        res = ha_tools.start_replica_set(members)
        self.seed, self.name = res

        primary = ha_tools.get_primary()
        self.primary = _partition_node(primary)
        self.primary_tags = ha_tools.get_tags(primary)
        # Make sure priority worked
        self.assertEqual('primary', self.primary_tags['name'])

        self.primary_dc = {'dc': self.primary_tags['dc']}

        secondaries = ha_tools.get_secondaries()

        (secondary, ) = [
            s for s in secondaries
            if ha_tools.get_tags(s)['name'] == 'secondary']

        self.secondary = _partition_node(secondary)
        self.secondary_tags = ha_tools.get_tags(secondary)
        self.secondary_dc = {'dc': self.secondary_tags['dc']}

        (other_secondary, ) = [
            s for s in secondaries
            if ha_tools.get_tags(s)['name'] == 'other_secondary']

        self.other_secondary = _partition_node(other_secondary)
        self.other_secondary_tags = ha_tools.get_tags(other_secondary)
        self.other_secondary_dc = {'dc': self.other_secondary_tags['dc']}

        # Synchronous PyMongo interfaces for convenience
        self.c = pymongo.mongo_replica_set_client.MongoReplicaSetClient(
            self.seed, replicaSet=self.name)
        self.db = self.c.motor_test
        self.w = len(self.c.secondaries) + 1
        self.db.test.remove({}, w=self.w)
        self.db.test.insert(
            [{'foo': i} for i in range(10)], w=self.w)

        self.clear_ping_times()

    def set_ping_time(self, host, ping_time_seconds):
        Member._host_to_ping_time[host] = ping_time_seconds

    def clear_ping_times(self):
        Member._host_to_ping_time.clear()

    @gen_test(timeout=240)
    def test_read_preference(self):
        # This is long, but we put all the tests in one function to save time
        # on setUp, which takes about 30 seconds to bring up a replica set.
        # We pass through four states:
        #
        #       1. A primary and two secondaries
        #       2. Primary down
        #       3. Primary up, one secondary down
        #       4. Primary up, all secondaries down
        #
        # For each state, we verify the behavior of PRIMARY,
        # PRIMARY_PREFERRED, SECONDARY, SECONDARY_PREFERRED, and NEAREST
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()

        @gen.coroutine
        def read_from_which_host(
            rsc,
            mode,
            tag_sets=None,
            latency=15,
        ):
            db = rsc.motor_test
            db.read_preference = mode
            if isinstance(tag_sets, dict):
                tag_sets = [tag_sets]
            db.tag_sets = tag_sets or [{}]
            db.secondary_acceptable_latency_ms = latency

            cursor = db.test.find()
            try:
                yield cursor.fetch_next
                raise gen.Return(cursor.delegate._Cursor__connection_id)
            except AutoReconnect:
                raise gen.Return(None)

        @gen.coroutine
        def assert_read_from(member, *args, **kwargs):
            for _ in range(10):
                used = yield read_from_which_host(c, *args, **kwargs)
                self.assertEqual(member, used)

        @gen.coroutine
        def assert_read_from_all(members, *args, **kwargs):
            members = set(members)
            all_used = set()
            for _ in range(100):
                used = yield read_from_which_host(c, *args, **kwargs)
                all_used.add(used)
                if members == all_used:
                    raise gen.Return()  # Success

            # This will fail
            self.assertEqual(members, all_used)

        def unpartition_node(node):
            host, port = node
            return '%s:%s' % (host, port)

        primary = self.primary
        secondary = self.secondary
        other_secondary = self.other_secondary

        bad_tag = {'bad': 'tag'}

        # 1. THREE MEMBERS UP -------------------------------------------------
        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        # Trivial: mode and tags both match
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.primary_dc)

        # Secondary matches but not primary, choose primary
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.secondary_dc)

        # Chooses primary, ignoring tag sets
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.primary_dc)

        # Chooses primary, ignoring tag sets
        yield assert_read_from(primary, PRIMARY_PREFERRED, bad_tag)
        yield assert_read_from(primary, PRIMARY_PREFERRED, [bad_tag, {}])

        #       SECONDARY
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY, latency=9999999)

        #       SECONDARY_PREFERRED
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY_PREFERRED, latency=9999999)

        # Multiple tags
        yield assert_read_from(
            secondary, SECONDARY_PREFERRED, self.secondary_tags)

        # Fall back to primary if it's the only one matching the tags
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'primary'})

        # No matching secondaries
        yield assert_read_from(primary, SECONDARY_PREFERRED, bad_tag)

        # Fall back from non-matching tag set to matching set
        yield assert_read_from_all(
            [secondary, other_secondary],
            SECONDARY_PREFERRED, [bad_tag, {}], latency=9999999)

        yield assert_read_from(
            other_secondary,
            SECONDARY_PREFERRED, [bad_tag, {'dc': 'ny'}])

        #       NEAREST
        self.clear_ping_times()

        yield assert_read_from_all(
            [primary, secondary, other_secondary], NEAREST, latency=9999999)

        yield assert_read_from_all(
            [primary, other_secondary],
            NEAREST, [bad_tag, {'dc': 'ny'}], latency=9999999)

        self.set_ping_time(primary, 0)
        self.set_ping_time(secondary, .03)  # 30 milliseconds.
        self.set_ping_time(other_secondary, 10)

        # Nearest member, no tags
        yield assert_read_from(primary, NEAREST)

        # Tags override nearness
        yield assert_read_from(primary, NEAREST, {'name': 'primary'})
        yield assert_read_from(secondary, NEAREST, self.secondary_dc)

        # Make secondary fast
        self.set_ping_time(primary, .03)  # 30 milliseconds.
        self.set_ping_time(secondary, 0)

        yield assert_read_from(secondary, NEAREST)

        # Other secondary fast
        self.set_ping_time(secondary, 10)
        self.set_ping_time(other_secondary, 0)

        yield assert_read_from(other_secondary, NEAREST)

        # High secondaryAcceptableLatencyMS, should read from all members
        yield assert_read_from_all(
            [primary, secondary, other_secondary],
            NEAREST, latency=9999999)

        self.clear_ping_times()

        yield assert_read_from_all(
            [primary, other_secondary], NEAREST, [{'dc': 'ny'}],
            latency=9999999)

        # 2. PRIMARY DOWN -----------------------------------------------------
        killed = ha_tools.kill_primary()

        # Let monitor notice primary's gone
        yield self.pause(2 * MONITOR_INTERVAL)

        #       PRIMARY
        yield assert_read_from(None, PRIMARY)

        #       PRIMARY_PREFERRED
        # No primary, choose matching secondary
        yield assert_read_from_all(
            [secondary, other_secondary], PRIMARY_PREFERRED, latency=9999999)

        yield assert_read_from(
            secondary, PRIMARY_PREFERRED, {'name': 'secondary'})

        # No primary or matching secondary
        yield assert_read_from(None, PRIMARY_PREFERRED, bad_tag)

        #       SECONDARY
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY, latency=9999999)

        # Only primary matches
        yield assert_read_from(None, SECONDARY, {'name': 'primary'})

        # No matching secondaries
        yield assert_read_from(None, SECONDARY, bad_tag)

        #       SECONDARY_PREFERRED
        yield assert_read_from_all(
            [secondary, other_secondary], SECONDARY_PREFERRED, latency=9999999)

        # Mode and tags both match
        yield assert_read_from(
            secondary, SECONDARY_PREFERRED, {'name': 'secondary'})

        #       NEAREST
        self.clear_ping_times()

        yield assert_read_from_all(
            [secondary, other_secondary], NEAREST, latency=9999999)

        # 3. PRIMARY UP, ONE SECONDARY DOWN -----------------------------------
        ha_tools.restart_members([killed])

        for _ in range(30):
            if ha_tools.get_primary():
                break
            yield self.pause(1)
        else:
            self.fail("Primary didn't come back up")

        ha_tools.kill_members([unpartition_node(secondary)], 2)
        self.assertTrue(pymongo.MongoClient(
            unpartition_node(primary),
            slave_okay=True
        ).admin.command('ismaster')['ismaster'])

        yield self.pause(2 * MONITOR_INTERVAL)

        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        yield assert_read_from(primary, PRIMARY_PREFERRED)

        #       SECONDARY
        yield assert_read_from(other_secondary, SECONDARY)
        yield assert_read_from(
            other_secondary, SECONDARY, self.other_secondary_dc)

        # Only the down secondary matches
        yield assert_read_from(None, SECONDARY, {'name': 'secondary'})

        #       SECONDARY_PREFERRED
        yield assert_read_from(other_secondary, SECONDARY_PREFERRED)
        yield assert_read_from(
            other_secondary, SECONDARY_PREFERRED, self.other_secondary_dc)

        # The secondary matching the tag is down, use primary
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'secondary'})

        #       NEAREST
        yield assert_read_from_all(
            [primary, other_secondary], NEAREST, latency=9999999)

        yield assert_read_from(
            other_secondary, NEAREST, {'name': 'other_secondary'})

        yield assert_read_from(primary, NEAREST, {'name': 'primary'})

        # 4. PRIMARY UP, ALL SECONDARIES DOWN ---------------------------------
        ha_tools.kill_members([unpartition_node(other_secondary)], 2)
        self.assertTrue(pymongo.MongoClient(
            unpartition_node(primary),
            slave_okay=True
        ).admin.command('ismaster')['ismaster'])

        #       PRIMARY
        yield assert_read_from(primary, PRIMARY)

        #       PRIMARY_PREFERRED
        yield assert_read_from(primary, PRIMARY_PREFERRED)
        yield assert_read_from(primary, PRIMARY_PREFERRED, self.secondary_dc)

        #       SECONDARY
        yield assert_read_from(None, SECONDARY)
        yield assert_read_from(None, SECONDARY, self.other_secondary_dc)
        yield assert_read_from(None, SECONDARY, {'dc': 'ny'})

        #       SECONDARY_PREFERRED
        yield assert_read_from(primary, SECONDARY_PREFERRED)
        yield assert_read_from(primary, SECONDARY_PREFERRED, self.secondary_dc)
        yield assert_read_from(
            primary, SECONDARY_PREFERRED, {'name': 'secondary'})

        yield assert_read_from(primary, SECONDARY_PREFERRED, {'dc': 'ny'})

        #       NEAREST
        yield assert_read_from(primary, NEAREST)
        yield assert_read_from(None, NEAREST, self.secondary_dc)
        yield assert_read_from(None, NEAREST, {'name': 'secondary'})

        # Even if primary's slow, still read from it
        self.set_ping_time(primary, 100)
        yield assert_read_from(primary, NEAREST)
        yield assert_read_from(None, NEAREST, self.secondary_dc)

        self.clear_ping_times()

    def tearDown(self):
        self.c.close()
        self.clear_ping_times()
        super(MotorTestReadPreference, self).tearDown()


class MotorTestReplicaSetAuth(MotorHATestCase):
    def setUp(self):
        super(MotorTestReplicaSetAuth, self).setUp()
        members = [
            {},
            {'priority': 0},
            {'priority': 0},
        ]

        res = ha_tools.start_replica_set(members, auth=True)
        self.seed, self.name = res
        self.c = pymongo.mongo_replica_set_client.MongoReplicaSetClient(
            self.seed, replicaSet=self.name)

        self.c.admin.add_user('admin', password='adminpass',
                              roles=['userAdminAnyDatabase'])
        self.c.admin.authenticate('admin', 'adminpass')
        self.c.pymongo_ha_auth.add_user('user', 'userpass', roles=['readWrite'])
        self.c.pymongo_ha_auth.authenticate('user', 'userpass')

        # Await replication.
        self.c.pymongo_ha_auth.collection.insert({}, w=3, wtimeout=30000)
        self.c.pymongo_ha_auth.collection.remove({}, w=3, wtimeout=30000)

    @gen_test(timeout=30)
    def test_auth_during_failover(self):
        c = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield c.open()
        db = c.pymongo_ha_auth
        res = yield db.authenticate('user', 'userpass')
        self.assertTrue(res)
        yield db.foo.insert({'foo': 'bar'}, w=3, wtimeout=30000)
        yield db.logout()
        with assert_raises(OperationFailure):
            yield db.foo.find_one()

        primary = '%s:%d' % self.c.primary
        ha_tools.kill_members([primary], 2)

        # Let monitor notice primary's gone
        yield self.pause(2 * MONITOR_INTERVAL)

        # Make sure we can still authenticate
        res = yield db.authenticate('user', 'userpass')
        self.assertTrue(res)

        # And still query.
        db.read_preference = PRIMARY_PREFERRED
        res = yield db.foo.find_one()
        self.assertEqual('bar', res['foo'])
        c.close()

    def tearDown(self):
        self.c.close()
        super(MotorTestReplicaSetAuth, self).tearDown()


class MotorTestAlive(MotorHATestCase):
    def setUp(self):
        super(MotorTestAlive, self).setUp()
        members = [{}, {}]
        self.seed, self.name = ha_tools.start_replica_set(members)

    @gen_test
    def test_alive(self):
        primary = ha_tools.get_primary()
        secondary = ha_tools.get_random_secondary()
        primary_cx = yield motor.MotorClient(primary).open()
        secondary_cx = yield motor.MotorClient(secondary).open()
        rsc = motor.MotorReplicaSetClient(self.seed, replicaSet=self.name)
        yield rsc.open()
        try:
            self.assertTrue((yield primary_cx.alive()))
            self.assertTrue((yield secondary_cx.alive()))
            self.assertTrue((yield rsc.alive()))

            ha_tools.kill_primary()
            yield self.pause(2)

            self.assertFalse((yield primary_cx.alive()))
            self.assertTrue((yield secondary_cx.alive()))
            self.assertFalse((yield rsc.alive()))

            ha_tools.kill_members([secondary], 2)
            yield self.pause(2)

            self.assertFalse((yield primary_cx.alive()))
            self.assertFalse((yield secondary_cx.alive()))
            self.assertFalse((yield rsc.alive()))
        finally:
            rsc.close()


class MotorTestMongosHighAvailability(MotorHATestCase):
    def setUp(self):
        super(MotorTestMongosHighAvailability, self).setUp()
        self.seed_list = ha_tools.create_sharded_cluster()

    @gen_test(timeout=30)
    def test_mongos_ha(self):
        dbname = 'pymongo_mongos_ha'
        c = yield motor.MotorClient(self.seed_list).open()
        yield c.drop_database(dbname)
        coll = c[dbname].test
        yield coll.insert({'foo': 'bar'})

        first = '%s:%d' % (c.host, c.port)
        ha_tools.kill_mongos(first)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()
        # Find new mongos
        self.assertEqual(1, (yield coll.count()))

        second = '%s:%d' % (c.host, c.port)
        self.assertNotEqual(first, second)
        ha_tools.kill_mongos(second)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()
        # Find new mongos
        self.assertEqual(1, (yield coll.count()))

        third = '%s:%d' % (c.host, c.port)
        self.assertNotEqual(second, third)
        ha_tools.kill_mongos(third)
        yield self.pause(1)
        # Fail first attempt
        with assert_raises(AutoReconnect):
            yield coll.count()

        # We've killed all three, restart one.
        ha_tools.restart_mongos(first)
        yield self.pause(1)

        # Find new mongos
        self.assertEqual(1, (yield coll.count()))


if __name__ == '__main__':
    if not ha_tools.tornado_warnings:
        suppress_tornado_warnings()

    unittest.main()
