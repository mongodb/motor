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

"""Test Motor by testing that Synchro, a fake PyMongo implementation built on
top of Motor, passes the same unittests as PyMongo.

This program monkey-patches sys.modules, so run it alone, rather than as part
of a larger test suite.
"""

import importlib
import importlib.abc
import importlib.machinery
import sys

import nose
from nose.config import Config
from nose.plugins import Plugin
from nose.plugins.manager import PluginManager
from nose.plugins.skip import Skip
from nose.plugins.xunit import Xunit
from nose.selector import Selector

import synchro

excluded_modules = [
    # Exclude some PyMongo tests that can't be applied to Synchro.
    "test.test_examples",
    "test.test_threads",
    "test.test_pooling",
    "test.test_saslprep",
    # Complex PyMongo-specific mocking.
    "test.test_replica_set_reconfig",
    # Accesses PyMongo internals.
    "test.test_retryable_writes",
    # Accesses PyMongo internals. Tested directly in Motor.
    "test.test_session",
    # Deprecated in PyMongo, removed in Motor 2.0.
    "test.test_gridfs",
    # Skip mypy tests.
    "test.test_mypy",
]


excluded_tests = [
    # Motor's reprs aren't the same as PyMongo's.
    "*.test_repr",
    "TestClient.test_unix_socket",
    # Motor extends the handshake metadata.
    "ClientUnitTest.test_metadata",
    # Lazy-connection tests require multithreading; we test concurrent
    # lazy connection directly.
    "TestClientLazyConnect.*",
    # Motor doesn't support forking or threading.
    "*.test_interrupt_signal",
    "TestSCRAM.test_scram_threaded",
    "TestGSSAPI.test_gssapi_threaded",
    "TestCursor.test_concurrent_close",
    # These are in test_gridfs_bucket.
    "TestGridfs.test_threaded_reads",
    "TestGridfs.test_threaded_writes",
    # Can't do MotorCollection(name, create=True), Motor constructors do no I/O.
    "TestCollection.test_create",
    # Requires indexing / slicing cursors, which Motor doesn't do, see MOTOR-84.
    "TestCollection.test_min_query",
    "TestCursor.test_clone",
    "TestCursor.test_clone_empty",
    "TestCursor.test_getitem_numeric_index",
    "TestCursor.test_getitem_slice_index",
    "TestCursor.test_tailable",
    "TestRawBatchCursor.test_get_item",
    "TestRawBatchCommandCursor.test_get_item",
    # No context-manager protocol for MotorCursor.
    "TestCursor.test_with_statement",
    # Motor's cursors initialize lazily.
    "TestRawBatchCommandCursor.test_monitoring",
    # Can't iterate a GridOut in Motor.
    "TestGridFile.test_iterator",
    "TestGridfs.test_missing_length_iter",
    # No context-manager protocol for MotorGridIn, and can't set attrs.
    "TestGridFile.test_context_manager",
    "TestGridFile.test_grid_in_default_opts",
    "TestGridFile.test_set_after_close",
    # GridOut always connects lazily in Motor.
    "TestGridFile.test_grid_out_lazy_connect",
    "TestGridfs.test_gridfs_lazy_connect",  # In test_gridfs_bucket.
    # Complex PyMongo-specific mocking.
    "*.test_wire_version",
    "TestClient.test_heartbeat_frequency_ms",
    "TestExhaustCursor.*",
    "TestHeartbeatMonitoring.*",
    "TestMongoClientFailover.*",
    "TestMongosLoadBalancing.*",
    "TestSSL.test_system_certs_config_error",
    "TestCMAP.test_cmap_wait_queue_timeout_must_aggressively_timeout_threads_enqueued_longer_than_waitQueueTimeoutMS",
    # Accesses PyMongo internals.
    "TestClient.test_close_kills_cursors",
    "TestClient.test_stale_getmore",
    "TestClient.test_direct_connection",
    "TestCollection.test_aggregation_cursor",
    "TestCommandAndReadPreference.*",
    "TestCommandMonitoring.test_get_more_failure",
    "TestCommandMonitoring.test_sensitive_commands",
    "TestCursor.test_allow_disk_use",
    "TestCursor.test_close_kills_cursor_synchronously",
    "TestCursor.test_delete_not_initialized",
    "TestGridFile.test_grid_out_cursor_options",
    "TestGridFile.test_survive_cursor_not_found",
    "TestMaxStaleness.test_last_write_date",
    "TestSelections.test_bool",
    "TestCollation.*",
    "TestCollection.test_find_one_and_write_concern",
    "TestCollection.test_write_error_text_handling",
    "TestBinary.test_uuid_queries",
    "TestCursor.test_comment",
    "TestCursor.test_where",
    "TestGridfs.test_gridfs_find",
    # Tests that use "authenticate" or "logoout", removed in Motor 2.0.
    "TestSASLPlain.test_sasl_plain_bad_credentials",
    "TestSCRAM.test_scram",
    "TestSCRAMSHA1.test_scram_sha1",
    # Uses "collection_names", deprecated in PyMongo, removed in Motor 2.0.
    "TestSingleSecondaryOk.test_reads_from_secondary",
    # Slow.
    "TestDatabase.test_list_collection_names",
    # MOTOR-425 these tests fail with duplicate key errors.
    "TestClusterChangeStreamsWCustomTypes.*",
    "TestCollectionChangeStreamsWCustomTypes.*",
    "TestDatabaseChangeStreamsWCustomTypes.*",
    # Tests that use warnings.catch_warnings which don't show up in Motor.
    "TestCursor.test_min_max_without_hint",
    # TODO: MOTOR-606
    "TestTransactionsConvenientAPI.*",
    "TestTransactions.test_create_collection",
    # Motor's change streams need Python 3.5 to support async iteration but
    # these change streams tests spawn threads which don't work without an
    # IO loop.
    "*.test_next_blocks",
    "*.test_aggregate_cursor_blocks",
    # Can't run these tests because they use threads.
    "*.test_ignore_stale_connection_errors",
    "*.test_pool_paused_error_is_retryable",
    # Needs synchro.GridFS class, see MOTOR-609.
    "TestTransactions.test_gridfs_does_not_support_transactions",
    # PYTHON-3228 _tmp_session should validate session input
    "*.test_helpers_with_let",
    # Relies on comment being in the method signatures, which would force use
    # to rewrite much of AgnosticCollection.
    "*.test_collection_helpers",
    "*.test_database_helpers",
    "*.test_client_helpers",
    # This test is too slow given all of the wrapping logic.
    "*.test_transaction_starts_with_batched_write",
    # This test is too flaky given all the wrapping logic.
    "TestProse.test_load_balancing",
    # This feature is going away in PyMongo 5
    "*.test_iteration",
    # MD5 is deprecated
    "*.test_md5",
    # Causes a deadlock.
    "TestFork.*",
    # Also causes a deadlock.
    "TestClientSimple.test_fork",
    # These methods are picked up by nose despite not being a unittest.
    "TestRewrapWithSeparateClientEncryption.run_test",
    "TestCustomEndpoint.run_test_expected_success",
    "TestDataKeyDoubleEncryption.run_test",
    # Motor does not support CSOT.
    "TestCsotGridfsFind.*",
    # These tests are failing right now.
    "TestUnifiedFindShutdownError.test_Concurrent_shutdown_error_on_find",
    "TestUnifiedInsertShutdownError.test_Concurrent_shutdown_error_on_insert",
    "TestUnifiedPoolClearedError.test_PoolClearedError_does_not_mark_server_unknown",
]


excluded_modules_matched = set()
excluded_tests_matched = set()


class SynchroNosePlugin(Plugin):
    name = "synchro"

    def __init__(self, *args, **kwargs):
        # We need a standard Nose selector in order to filter out methods that
        # don't match TestSuite.test_*
        self.selector = Selector(config=None)
        super().__init__(*args, **kwargs)

    def configure(self, options, conf):
        super().configure(options, conf)
        self.enabled = True

    def wantModule(self, module):
        # Depending on PYTHONPATH, Motor's direct tests may be imported - don't
        # run them now.
        if module.__name__.startswith("test.test_motor_"):
            return False

        for module_name in excluded_modules:
            if module_name.endswith("*"):
                if module.__name__.startswith(module_name.rstrip("*")):
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
        if fn.__name__ in (
            "test_cases",
            "create_spec_test",
            "create_test",
            "create_tests",
            "create_connection_string_test",
            "create_document_test",
            "create_operation_test",
            "create_selection_tests",
            "generate_test_classes",
        ):
            return False

    def wantClass(self, cls):
        # PyMongo's test generator classes run at import time; tell Nose not
        # to run them as unittests.
        if cls.__name__ in ("TestCreator",):
            return False

    def wantMethod(self, method):
        # Run standard Nose checks on name, like "does it start with test_"?
        if not self.selector.matches(method.__name__):
            return False

        if method.__name__ in ("run_test_ops", "maybe_skip_test"):
            return False

        for excluded_name in excluded_tests:
            classname = method.__self__.__class__.__name__

            # Should we exclude this method's whole TestCase?
            suite_name, method_name = excluded_name.split(".")
            suite_matches = suite_name in [classname, "*"]

            # Should we exclude this particular method?
            method_matches = method.__name__ == method_name or method_name == "*"

            if suite_matches and method_matches:
                excluded_tests_matched.add(excluded_name)
                return False

        return True


class SynchroModuleFinder(importlib.abc.MetaPathFinder):
    def __init__(self):
        self._loader = SynchroModuleLoader()

    def find_spec(self, fullname, path, target=None):
        if self._loader.patch_spec(fullname):
            return importlib.machinery.ModuleSpec(fullname, self._loader)

        # Let regular module search continue.
        return None


class SynchroModuleLoader(importlib.abc.Loader):
    def patch_spec(self, fullname):
        parts = fullname.split(".")
        if parts[-1] in ("gridfs", "pymongo"):
            # E.g. "import pymongo"
            return True
        elif len(parts) >= 2 and parts[-2] in ("gridfs", "pymongo"):
            # E.g. "import pymongo.mongo_client"
            return True

        return False

    def exec_module(self, module):
        pass

    def create_module(self, spec):
        if self.patch_spec(spec.name):
            return synchro

        # Let regular module search continue.
        return None


if __name__ == "__main__":
    try:
        # Enable the fault handler to dump the traceback of each running
        # thread
        # after a segfault.
        import faulthandler

        faulthandler.enable()
        # Dump the tracebacks of all threads after 25 minutes.
        if hasattr(faulthandler, "dump_traceback_later"):
            faulthandler.dump_traceback_later(25 * 60)
    except ImportError:
        pass

    # Monkey-patch all pymongo's unittests so they think Synchro is the
    # real PyMongo.
    sys.meta_path[0:0] = [SynchroModuleFinder()]
    # Delete the cached pymongo/gridfs modules so that SynchroModuleFinder will
    # be invoked in Python 3, see
    # https://docs.python.org/3/reference/import.html#import-hooks
    for n in [
        "pymongo",
        "pymongo.collection",
        "pymongo.client_session",
        "pymongo.command_cursor",
        "pymongo.change_stream",
        "pymongo.cursor",
        "pymongo.encryption",
        "pymongo.encryption_options",
        "pymongo.mongo_client",
        "pymongo.database",
        "gridfs",
        "gridfs.grid_file",
    ]:
        sys.modules.pop(n)

    if "--check-exclude-patterns" in sys.argv:
        check_exclude_patterns = True
        sys.argv.remove("--check-exclude-patterns")
    else:
        check_exclude_patterns = False

    success = nose.run(
        config=Config(plugins=PluginManager()), addplugins=[SynchroNosePlugin(), Skip(), Xunit()]
    )

    if not success:
        sys.exit(1)

    if check_exclude_patterns:
        unused_module_pats = set(excluded_modules) - excluded_modules_matched
        assert not unused_module_pats, "Unused module patterns: %s" % (unused_module_pats,)

        unused_test_pats = set(excluded_tests) - excluded_tests_matched
        assert not unused_test_pats, "Unused test patterns: %s" % (unused_test_pats,)
