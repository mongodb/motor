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

"""Test Motor by testing that Synchro, a fake PyMongo implementation built on
top of Motor, passes the same unittests as PyMongo.

This program monkey-patches sys.modules, so run it alone, rather than as part
of a larger test suite.

The environment variable TIMEOUT_SEC controls how long Synchro waits for each
Motor operation to complete, default 5 seconds.
"""

import sys
import synchro

import nose
from nose.config import Config
from nose.plugins import Plugin
from nose.plugins.manager import PluginManager
from nose.plugins.skip import Skip
from nose.plugins.xunit import Xunit
from nose.selector import Selector

excluded_modules = [
    # Depending on PYTHONPATH, Motor's direct tests may be imported - don't
    # run them now.
    'test.test_motor_',

    # Exclude some PyMongo tests that can't be applied to Synchro.
    'test.test_threads',
    'test.test_threads_replica_set_client',
    'test.test_pooling',
    'test.test_pooling_gevent',
    'test.test_paired',
    'test.test_master_slave_connection',
    'test.test_legacy_connections',
]

excluded_tests = [
    # Synchro can't simulate requests, so test copy_db in Motor directly
    '*.test_copy_db',

    # use_greenlets is always True with Motor
    '*.test_use_greenlets',

    # Motor's reprs aren't the same as PyMongo's
    '*.test_repr',

    # Motor doesn't do requests
    '*.test_auto_start_request',
    '*.test_nested_request',
    '*.test_request_threads',
    '*.test_operation_failure_with_request',
    'TestClient.test_with_start_request',
    'TestDatabase.test_authenticate_and_request',
    'TestGridfs.test_request',
    'TestGridfs.test_gridfs_request',

    # We test this directly, because it requires monkey-patching either socket
    # or IOStream, depending on whether it's PyMongo or Motor
    'TestReplicaSetClient.test_auto_reconnect_exception_when_read_preference_is_secondary',

    # No pinning in Motor since there are no requests
    'TestReplicaSetClient.test_pinned_member',

    # test_read_preference: requires patching MongoReplicaSetClient specially
    'TestCommandAndReadPreference.*',

    # Motor doesn't support forking or threading
    '*.test_interrupt_signal',
    '*.test_fork',
    'TestCollection.test_ensure_unique_index_threaded',
    'TestGridfs.test_threaded_writes',
    'TestGridfs.test_threaded_reads',

    # Motor doesn't support PyMongo's syntax, db.system_js['my_func'] = "code",
    # users should just use system.js as a regular collection
    'TestDatabase.test_system_js',
    'TestDatabase.test_system_js_list',

    # Motor can't raise an index error if a cursor slice is out of range; it
    # just gets no results
    'TestCursor.test_getitem_index_out_of_range',

    # Motor's tailing works differently
    'TestCursor.test_tailable',

    # No context-manager protocol for MotorCursor
    'TestCursor.test_with_statement',

    # Can't iterate a GridOut in Motor
    'TestGridfs.test_missing_length_iter',
    'TestGridFile.test_iterator',

    # Don't need to check that GridFile is deprecated
    'TestGridFile.test_grid_file',

    # No context-manager protocol for MotorGridIn, and can't set attrs
    'TestGridFile.test_context_manager',
    'TestGridFile.test_grid_in_default_opts',
    'TestGridFile.test_set_after_close',
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
            if module.__name__.startswith(module_name):
                return False

        return True

    def wantMethod(self, method):
        # Run standard Nose checks on name, like "does it start with test_"?
        if not self.selector.matches(method.__name__):
            return False

        for excluded_name in excluded_tests:
            suite_name, method_name = excluded_name.split('.')
            suite_matches = (
                method.im_class.__name__ == suite_name or suite_name == '*')

            method_matches = (
                method.__name__ == method_name or method_name == '*')

            if suite_matches and method_matches:
                return False

        return True


if __name__ == '__main__':
    # Monkey-patch all pymongo's unittests so they think Synchro is the
    # real PyMongo
    sys.modules['pymongo'] = synchro

    for mod in [
        'pymongo.auth',
        'pymongo.mongo_client',
        'pymongo.collection',
        'pymongo.mongo_replica_set_client',
        'pymongo.master_slave_connection',
        'pymongo.database',
        'pymongo.pool',
        'pymongo.thread_util',
        'gridfs',
        'gridfs.errors',
        'gridfs.grid_file',
    ]:
        # So that e.g. 'from pymongo.mongo_client import MongoClient' gets the
        # Synchro MongoClient, not the real one. We include
        # master_slave_connection, even though Motor doesn't support it and
        # we exclude it from tests, so that the import doesn't fail.
        sys.modules[mod] = synchro

    # Ensure time.sleep() acts as PyMongo's tests expect: background tasks
    # can run to completion while foreground pauses
    sys.modules['time'] = synchro.TimeModule()

    nose.main(
        config=Config(plugins=PluginManager()),
        addplugins=[SynchroNosePlugin(), Skip(), Xunit()])
