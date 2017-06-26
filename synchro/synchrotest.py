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

from __future__ import unicode_literals

"""Test Motor by testing that Synchro, a fake PyMongo implementation built on
top of Motor, passes the same unittests as PyMongo.

This program monkey-patches sys.modules, so run it alone, rather than as part
of a larger test suite.
"""

import sys

import nose
from nose.config import Config
from nose.plugins import Plugin
from nose.plugins.manager import PluginManager
from nose.plugins.skip import Skip
from nose.plugins.xunit import Xunit
from nose.selector import Selector

import synchro
from motor.motor_py3_compat import PY3

excluded_modules = [
    # Depending on PYTHONPATH, Motor's direct tests may be imported - don't
    # run them now.
    'test.test_motor_',

    # Exclude some PyMongo tests that can't be applied to Synchro.
    'test.test_cursor_manager',
    'test.test_threads',
    'test.test_threads_replica_set_client',
    'test.test_pooling',

    # Complex PyMongo-specific mocking.
    'test.test_replica_set_reconfig',
    'test.test_mongos_ha',
]

excluded_tests = [
    # Motor's reprs aren't the same as PyMongo's.
    '*.test_repr',
    '*.test_repr_replica_set',
    'TestClient.test_unix_socket',

    # Lazy-connection tests require multithreading; we test concurrent
    # lazy connection directly.
    'TestClientLazyConnect.*',

    # Motor doesn't support forking or threading.
    '*.test_fork',
    '*.test_interrupt_signal',
    'TestCollection.test_ensure_unique_index_threaded',
    'TestGridfs.test_threaded_reads',
    'TestGridfs.test_threaded_writes',
    'TestLegacy.test_ensure_index_threaded',
    'TestLegacy.test_ensure_purge_index_threaded',
    'TestLegacy.test_ensure_unique_index_threaded',
    'TestThreadsAuth.*',
    'TestThreadsAuthReplicaSet.*',
    'TestGSSAPI.test_gssapi_threaded',

    # Relies on threads; tested directly.
    'TestCollection.test_parallel_scan',

    # Motor's aggregate API is different, always sends "cursor={}" by default.
    'TestCollection.test_aggregate',
    'TestCollection.test_aggregate_raw_bson',
    'TestAllScenarios.test_read_aggregate_Aggregate_with_multiple_stages',
    'TestSingleSlaveOk.test_reads_from_secondary',

    # Can't do MotorCollection(name, create=True), Motor constructors do no I/O.
    'TestCollection.test_create',
    'TestCollection.test_reindex',

    # Motor doesn't support PyMongo's syntax, db.system_js['my_func'] = "code",
    # users should just use system.js as a regular collection.
    'TestDatabase.test_system_js',
    'TestDatabase.test_system_js_list',

    # Weird use-case.
    'TestCursor.test_cursor_transfer',

    # Requires indexing / slicing cursors, which Motor doesn't do, see MOTOR-84.
    'TestCollection.test_min_query',
    'TestCursor.test_clone',
    'TestCursor.test_count_with_limit_and_skip',
    'TestCursor.test_getitem_numeric_index',
    'TestCursor.test_getitem_slice_index',

    # No context-manager protocol for MotorCursor.
    'TestCursor.test_with_statement',

    # Can't iterate a GridOut in Motor.
    'TestGridFile.test_iterator',
    'TestGridfs.test_missing_length_iter',

    # Not worth simulating a user calling GridOutCursor(args).
    'TestGridFileNoConnect.test_grid_out_cursor_options',

    # No context-manager protocol for MotorGridIn, and can't set attrs.
    'TestGridFile.test_context_manager',
    'TestGridFile.test_grid_in_default_opts',
    'TestGridFile.test_set_after_close',

    # GridFS always connects lazily in Motor.
    'TestGridFile.test_grid_out_lazy_connect',
    'TestGridfs.test_gridfs_lazy_connect',

    # Complex PyMongo-specific mocking.
    '*.test_wire_version',
    'TestClient.test_heartbeat_frequency_ms',
    'TestClient.test_max_wire_version',
    'TestClient.test_wire_version_mongos_ha',
    'TestExhaustCursor.*',
    'TestHeartbeatMonitoring.*',
    'TestMongoClientFailover.*',
    'TestMongosLoadBalancing.*',
    'TestReplicaSetClientExhaustCursor.*',
    'TestReplicaSetClientInternalIPs.*',
    'TestReplicaSetClientMaxWriteBatchSize.*',
    'TestSSL.test_system_certs_config_error',

    # Motor is correct here, it's just unreliable on slow CI servers.
    'TestReplicaSetClient.test_timeout_does_not_mark_member_down',

    # Accesses PyMongo internals.
    'TestClient.test_kill_cursor_explicit_primary',
    'TestClient.test_kill_cursor_explicit_secondary',
    'TestClient.test_close_kills_cursors',
    'TestClient.test_stale_getmore',
    'TestCollection.test_aggregation_cursor',
    'TestCommandAndReadPreference.*',
    'TestCommandMonitoring.test_get_more_failure',
    'TestCommandMonitoring.test_sensitive_commands',
    'TestCursor.test_close_kills_cursor_synchronously',
    'TestGridFile.test_grid_out_cursor_options',
    'TestGridfsReplicaSet.test_gridfs_replica_set',
    'TestMaxStaleness.test_last_write_date_absent',
    'TestMonitor.test_atexit_hook',
    'TestReplicaSetClient.test_kill_cursor_explicit_primary',
    'TestReplicaSetClient.test_kill_cursor_explicit_secondary',
    'TestSelections.test_bool',
    'TestMaxStaleness.test_last_write_date',
]


excluded_modules_matched = set()
excluded_tests_matched = set()


class SynchroNosePlugin(Plugin):
    name = 'synchro'

    def __init__(self, *args, **kwargs):
        # We need a standard Nose selector in order to filter out methods that
        # don't match TestSuite.test_*
        self.selector = Selector(config=None)
        super(SynchroNosePlugin, self).__init__(*args, **kwargs)

    def configure(self, options, conf):
        super(SynchroNosePlugin, self).configure(options, conf)
        self.enabled = True

    def wantModule(self, module):
        for module_name in excluded_modules:
            if module_name.endswith('*'):
                if module.__name__.startswith(module_name.rstrip('*')):
                    # E.g., test_motor_cursor matches "test_motor_*".
                    excluded_modules_matched.add(module_name)
                    return False

            elif module.__name__ == module_name:
                return False

        return True

    def wantFunction(self, fn):
        # PyMongo's test generators run at import time; tell Nose not to run
        # them as unittests.
        if fn.__name__ in ('test_cases',
                           'create_test',
                           'create_selection_tests'):
            return False

    def wantMethod(self, method):
        # Run standard Nose checks on name, like "does it start with test_"?
        if not self.selector.matches(method.__name__):
            return False

        for excluded_name in excluded_tests:
            if PY3:
                classname = method.__self__.__class__.__name__
            else:
                classname = method.im_class.__name__

            # Should we exclude this method's whole TestCase?
            suite_name, method_name = excluded_name.split('.')
            suite_matches = (suite_name == classname or suite_name == '*')

            # Should we exclude this particular method?
            method_matches = (
                method.__name__ == method_name or method_name == '*')

            if suite_matches and method_matches:
                excluded_tests_matched.add(excluded_name)
                return False

        return True


# So that e.g. 'from pymongo.mongo_client import MongoClient' gets the
# Synchro MongoClient, not the real one.
class SynchroModuleFinder(object):
    def find_module(self, fullname, path=None):
        parts = fullname.split('.')
        if parts[-1] in ('gridfs', 'pymongo'):
            return SynchroModuleLoader(path)
        elif len(parts) >= 2 and parts[-2] in ('gridfs', 'pymongo'):
            return SynchroModuleLoader(path)

        # Let regular module search continue.
        return None


class SynchroModuleLoader(object):
    def __init__(self, path):
        self.path = path

    def load_module(self, fullname):
        return synchro


if __name__ == '__main__':
    # Monkey-patch all pymongo's unittests so they think Synchro is the
    # real PyMongo.
    sys.meta_path[0:0] = [SynchroModuleFinder()]

    # Ensure time.sleep() acts as PyMongo's tests expect: background tasks
    # can run to completion while foreground pauses.
    sys.modules['time'] = synchro.TimeModule()

    nose.main(
        config=Config(plugins=PluginManager()),
        addplugins=[SynchroNosePlugin(), Skip(), Xunit()])
    
    unused_module_patterns = set(excluded_modules) - excluded_modules_matched
    assert not unused_module_patterns, "Unused module patterns: %s" % (
        unused_module_patterns, )

    unused_test_patterns = set(excluded_tests) - excluded_tests_matched
    assert not unused_test_patterns, "Unused test patterns: %s" % (
        unused_test_patterns, )
