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
from motor.motor_py2_compat import PY3

excluded_modules = [
    # Exclude some PyMongo tests that can't be applied to Synchro.
    'test.test_cursor_manager',
    'test.test_examples',
    'test.test_threads',
    'test.test_pooling',
    'test.test_legacy_api',
    'test.test_monotonic',
    'test.test_saslprep',

    # Complex PyMongo-specific mocking.
    'test.test_replica_set_reconfig',

    # Accesses PyMongo internals.
    'test.test_retryable_writes',

    # Accesses PyMongo internals. Tested directly in Motor.
    'test.test_session',

    # We test Synchro in Python 2.7, but Motor's change streams need Python 3.
    'test.test_change_stream',

    # Deprecated in PyMongo, removed in Motor 2.0.
    'test.test_gridfs',
    'test.test_son_manipulator',
]

excluded_tests = [
    # Motor's reprs aren't the same as PyMongo's.
    '*.test_repr',
    'TestClient.test_unix_socket',

    # Motor extends the handshake metadata.
    'ClientUnitTest.test_metadata',

    # Lazy-connection tests require multithreading; we test concurrent
    # lazy connection directly.
    'TestClientLazyConnect.*',

    # Motor doesn't support forking or threading.
    '*.test_interrupt_signal',
    'TestSCRAM.test_scram_threaded',
    'TestGSSAPI.test_gssapi_threaded',
    'TestCursor.test_concurrent_close',
    # These are in test_gridfs_bucket.
    'TestGridfs.test_threaded_reads',
    'TestGridfs.test_threaded_writes',

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

    # Requires indexing / slicing cursors, which Motor doesn't do, see MOTOR-84.
    'TestCollection.test_min_query',
    'TestCursor.test_clone',
    'TestCursor.test_count_with_limit_and_skip',
    'TestCursor.test_getitem_numeric_index',
    'TestCursor.test_getitem_slice_index',
    'TestCursor.test_tailable',

    # Raw batches aren't implemented yet, MOTOR-172.
    'TestRawBatchCursor.*',
    'TestRawBatchCommandCursor.*',

    # No context-manager protocol for MotorCursor.
    'TestCursor.test_with_statement',

    # Can't iterate a GridOut in Motor.
    'TestGridFile.test_iterator',
    'TestGridfs.test_missing_length_iter',

    # No context-manager protocol for MotorGridIn, and can't set attrs.
    'TestGridFile.test_context_manager',
    'TestGridFile.test_grid_in_default_opts',
    'TestGridFile.test_set_after_close',

    # GridOut always connects lazily in Motor.
    'TestGridFile.test_grid_out_lazy_connect',
    'TestGridfs.test_gridfs_lazy_connect',  # In test_gridfs_bucket.

    # Complex PyMongo-specific mocking.
    '*.test_wire_version',
    'TestClient.test_heartbeat_frequency_ms',
    'TestExhaustCursor.*',
    'TestHeartbeatMonitoring.*',
    'TestMongoClientFailover.*',
    'TestMongosLoadBalancing.*',
    'TestReplicaSetClientInternalIPs.*',
    'TestReplicaSetClientMaxWriteBatchSize.*',
    'TestSSL.test_system_certs_config_error',

    # Motor is correct here, it's just unreliable on slow CI servers.
    'TestReplicaSetClient.test_timeout_does_not_mark_member_down',

    # Accesses PyMongo internals.
    'TestClient.test_close_kills_cursors',
    'TestClient.test_stale_getmore',
    'TestCollection.test_aggregation_cursor',
    'TestCommandAndReadPreference.*',
    'TestCommandMonitoring.test_get_more_failure',
    'TestCommandMonitoring.test_sensitive_commands',
    'TestCursor.test_close_kills_cursor_synchronously',
    'TestGridFile.test_grid_out_cursor_options',
    'TestMaxStaleness.test_last_write_date',
    'TestMaxStaleness.test_last_write_date_absent',
    'TestMonitor.test_atexit_hook',
    'TestReplicaSetClient.test_kill_cursor_explicit_primary',
    'TestReplicaSetClient.test_kill_cursor_explicit_secondary',
    'TestSelections.test_bool',
    'TestTransactions.transaction_test_debug',

    # Deprecated in PyMongo, removed in Motor 2.0.
    'TestDatabase.test_collection_names',
    'TestDatabase.test_errors',
    'TestDatabase.test_eval',
    'TestCollation.*',
    'TestCollection.test_find_one_and_write_concern',
    'TestCollection.test_parallel_scan_max_time_ms',
    'TestCollection.test_write_error_text_handling',
    'TestCommandMonitoring.test_legacy_insert_many',
    'TestCommandMonitoring.test_legacy_writes',
    'TestClient.test_database_names',

    # Tests that use "count", deprecated in PyMongo, removed in Motor 2.0.
    "*.test_command_monitoring_command_A_failed_command_event",
    "*.test_command_monitoring_command_A_successful_command",
    "*.test_command_monitoring_command_A_successful_command_with_a_non-primary_read_preference",
    "*.test_read_count-collation_Deprecated_count_with_collation",
    "*.test_read_count_Deprecated_count_with_a_filter",
    "*.test_read_count_Deprecated_count_without_a_filter",
    "TestBinary.test_uuid_queries",
    "TestCollection.test_count",
    "TestCursor.test_comment",
    "TestCursor.test_count",
    "TestCursor.test_count_with_fields",
    "TestCursor.test_count_with_hint",
    "TestCursor.test_where",
    "TestGridfs.test_gridfs_find",
    "TestTransactions.test_transactions_reads_count",
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
        # Depending on PYTHONPATH, Motor's direct tests may be imported - don't
        # run them now.
        if module.__name__.startswith('test.test_motor_'):
            return False

        for module_name in excluded_modules:
            if module_name.endswith('*'):
                if module.__name__.startswith(module_name.rstrip('*')):
                    # E.g., test_motor_cursor matches "test_motor_*".
                    excluded_modules_matched.add(module_name)
                    return False

            elif module.__name__ == module_name:
                excluded_modules_matched.add(module_name)
                return False

        return True

    def wantFunction(self, fn):
        # PyMongo's test generators run at import time; tell Nose not to run
        # them as unittests.
        if fn.__name__ in ('test_cases',
                           'create_test',
                           'create_connection_string_test',
                           'create_document_test',
                           'create_selection_tests',
                           ):
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

    if '--check-exclude-patterns' in sys.argv:
        check_exclude_patterns = True
        sys.argv.remove('--check-exclude-patterns')
    else:
        check_exclude_patterns = False

    success = nose.run(
        config=Config(plugins=PluginManager()),
        addplugins=[SynchroNosePlugin(), Skip(), Xunit()])

    if not success:
        sys.exit(1)

    if check_exclude_patterns:
        unused_module_pats = set(excluded_modules) - excluded_modules_matched
        assert not unused_module_pats, "Unused module patterns: %s" % (
            unused_module_pats, )

        unused_test_pats = set(excluded_tests) - excluded_tests_matched
        assert not unused_test_pats, "Unused test patterns: %s" % (
            unused_test_pats, )
