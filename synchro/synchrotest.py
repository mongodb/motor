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

    # Not worth simulating PyMongo's crazy deprecation semantics for safe and
    # slave_okay in Synchro.
    'test.test_common',

    # Exclude some PyMongo tests that can't be applied to Synchro.
    'test.test_threads',
    'test.test_threads_replica_set_client',
    'test.test_pooling',
    'test.test_pooling_gevent',
    'test.test_master_slave_connection',
    'test.test_legacy_connections',

    # Complex PyMongo-specific mocking.
    'test.test_replica_set_reconfig',
    'test.test_mongos_ha',
]

excluded_tests = [
    # Motor no longer has a copy_database method.
    '*.test_copy_db',

    # Depends on requests.
    'TestCollection.test_insert_large_batch',

    # Motor always uses greenlets.
    '*.test_use_greenlets',

    # Motor's reprs aren't the same as PyMongo's.
    '*.test_repr',

    # Not worth simulating PyMongo's crazy deprecation semantics for safe and
    # slave_okay in Synchro.
    'TestClient.test_from_uri',
    'TestReplicaSetClient.test_properties',

    # MotorClient(uri).open() doesn't raise ConfigurationError if the URI has
    # the wrong auth credentials.
    'TestClientAuth.test_auth_from_uri',

    # Motor's pool is different, we test it separately.
    '*.test_waitQueueMultiple',

    # Lazy-connection tests require multithreading; we test concurrent
    # lazy connection directly.
    'TestClientLazyConnect.*',
    'TestClientLazyConnectOneGoodSeed.*',
    'TestClientLazyConnectBadSeeds.*',
    'TestReplicaSetClientLazyConnect.*',
    'TestReplicaSetClientLazyConnectBadSeeds.*',

    # Motor doesn't do requests.
    '*.test_auto_start_request',
    '*.test_nested_request',
    '*.test_request_threads',
    '*.test_operation_failure_with_request',
    'TestClient.test_with_start_request',
    'TestCollection.test_unique_index',
    'TestDatabaseAuth.test_authenticate_and_request',
    'TestGridfs.test_request',
    'TestGridfs.test_gridfs_request',

    # We test this directly, because it requires monkey-patching either socket
    # or IOStream, depending on whether it's PyMongo or Motor.
    ('TestReplicaSetClient.'
     'test_auto_reconnect_exception_when_read_preference_is_secondary'),

    # No pinning in Motor since there are no requests.
    'TestReplicaSetClient.test_pinned_member',

    # Not allowed to call schedule_refresh directly in Motor.
    'TestReplicaSetClient.test_schedule_refresh',

    # We don't make the same guarantee as PyMongo when connecting an
    # RS client to a standalone.
    'TestReplicaSetClientAgainstStandalone.test_connect',

    # test_read_preference: requires patching MongoReplicaSetClient specially.
    'TestCommandAndReadPreference.*',

    # Motor doesn't support forking or threading.
    '*.test_interrupt_signal',
    '*.test_fork',
    'TestCollection.test_ensure_unique_index_threaded',
    'TestGridfs.test_threaded_writes',
    'TestGridfs.test_threaded_reads',
    'TestThreadsAuth.*',
    'TestThreadsAuthReplicaSet.*',

    # Relies on threads; tested directly.
    'TestCollection.test_parallel_scan',

    # Motor doesn't support PyMongo's syntax, db.system_js['my_func'] = "code",
    # users should just use system.js as a regular collection.
    'TestDatabase.test_system_js',
    'TestDatabase.test_system_js_list',

    # Weird use-case.
    'TestCursor.test_cursor_transfer',

    # No context-manager protocol for MotorCursor.
    'TestCursor.test_with_statement',

    # Can't iterate a GridOut in Motor.
    'TestGridfs.test_missing_length_iter',
    'TestGridFile.test_iterator',

    # Not worth simulating a user calling GridOutCursor(args).
    'TestGridFile.test_grid_out_cursor_options',

    # Don't need to check that GridFile is deprecated.
    'TestGridFile.test_grid_file',

    # No context-manager protocol for MotorGridIn, and can't set attrs.
    'TestGridFile.test_context_manager',
    'TestGridFile.test_grid_in_default_opts',
    'TestGridFile.test_set_after_close',

    # GridFS always connects lazily in Motor.
    'TestGridfs.test_gridfs_lazy_connect',

    # Testing a deprecated PyMongo API, Motor can skip it.
    'TestCollection.test_insert_message_creation',

    # Complex PyMongo-specific mocking.
    'TestMongoClientFailover.*',
    'TestReplicaSetClientInternalIPs.*',
    'TestReplicaSetClientMaxWriteBatchSize.*',
    'TestClient.test_wire_version_mongos_ha',
    'TestClient.test_max_wire_version',
    'TestExhaustCursor.*',
    'TestReplicaSetClientExhaustCursor.*',
    '*.test_wire_version',
]


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
                    return False

            elif module.__name__ == module_name:
                return False

        return True

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
                return False

        return True


# So that e.g. 'from pymongo.mongo_client import MongoClient' gets the
# Synchro MongoClient, not the real one. We include
# master_slave_connection, connection, etc. even though Motor doesn't support
# them and we exclude them from tests, so that the import doesn't fail.
pymongo_modules = set([
    'gridfs',
    'gridfs.errors',
    'gridfs.grid_file',
    'pymongo',
    'pymongo.auth',
    'pymongo.collection',
    'pymongo.common',
    'pymongo.connection',
    'pymongo.command_cursor',
    'pymongo.cursor',
    'pymongo.cursor_manager',
    'pymongo.database',
    'pymongo.helpers',
    'pymongo.errors',
    'pymongo.master_slave_connection',
    'pymongo.member',
    'pymongo.mongo_client',
    'pymongo.mongo_replica_set_client',
    'pymongo.pool',
    'pymongo.read_preferences',
    'pymongo.replica_set_connection',
    'pymongo.son_manipulator',
    'pymongo.ssl_match_hostname',
    'pymongo.thread_util',
    'pymongo.uri_parser',
])


class SynchroModuleFinder(object):
    def find_module(self, fullname, path=None):
        for module_name in pymongo_modules:
            if fullname.endswith(module_name):
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
