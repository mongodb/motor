# Copyright 2018-present MongoDB, Inc.
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

import collections
import os
import re

from bson import json_util
from bson.json_util import JSONOptions
from pymongo.read_concern import ReadConcern
from pymongo.results import (BulkWriteResult,
                             InsertManyResult,
                             InsertOneResult,
                             UpdateResult, DeleteResult)

from motor.motor_tornado import (MotorCommandCursor,
                                 MotorCursor,
                                 MotorLatentCommandCursor)

from test.version import Version

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""

import unittest

from pymongo import read_preferences, WriteConcern, \
    operations, ReadPreference, client_session, monitoring
from tornado import gen
from pymongo.errors import OperationFailure, PyMongoError
from tornado.testing import gen_test

from test import SkipTest
from test.test_environment import env
from test.tornado_tests import MotorTest

# Location of JSON test specifications.
_TEST_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), '../json/transactions')

_TXN_TESTS_DEBUG = os.environ.get('TRANSACTION_TESTS_DEBUG')


def camel_to_snake(camel):
    # Regex to convert CamelCase to snake_case.
    snake = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake).lower()


def camel_to_upper_camel(camel):
    return camel[0].upper() + camel[1:]


def camel_to_snake_args(arguments):
    for arg_name in list(arguments):
        c2s = camel_to_snake(arg_name)
        arguments[c2s] = arguments.pop(arg_name)
    return arguments


def parse_read_preference(pref):
    # Make first letter lowercase to match read_pref's modes.
    mode_string = pref.get('mode', 'primary')
    mode_string = mode_string[:1].lower() + mode_string[1:]
    mode = read_preferences.read_pref_mode_from_name(mode_string)
    max_staleness = pref.get('maxStalenessSeconds', -1)
    tag_sets = pref.get('tag_sets')
    return read_preferences.make_read_preference(
        mode, tag_sets=tag_sets, max_staleness=max_staleness)


def parse_opts(opts):
    parsed = {}
    if 'readPreference' in opts:
        parsed['read_preference'] = parse_read_preference(
            opts.pop('readPreference'))

    if 'writeConcern' in opts:
        parsed['write_concern'] = WriteConcern(**opts.pop('writeConcern'))

    if 'readConcern' in opts:
        parsed['read_concern'] = ReadConcern(**opts.pop('readConcern'))

    return parsed


def parse_args(args, sessions):
    parsed = parse_opts(args)

    if 'session' in args:
        assert sessions is not None
        parsed['session'] = sessions[args.pop('session')]

    return parsed


class OvertCommandListener(monitoring.CommandListener):
    """A CommandListener that ignores sensitive commands."""
    def __init__(self):
        self.results = collections.defaultdict(list)

    SENSITIVE = set(
        ["authenticate", "saslstart", "saslcontinue", "getnonce", "createuser",
         "updateuser", "copydbgetnonce", "copydbsaslstart", "copydb"])

    def started(self, event):
        if event.command_name.lower() not in self.SENSITIVE:
            self.results['started'].append(event)

    def succeeded(self, event):
        if event.command_name.lower() not in self.SENSITIVE:
            self.results['succeeded'].append(event)

    def failed(self, event):
        if event.command_name.lower() not in self.SENSITIVE:
            self.results['failed'].append(event)


class MotorTransactionTest(MotorTest):
    @classmethod
    def setUpClass(cls):
        super(MotorTransactionTest, cls).setUpClass()
        if not env.sessions_enabled:
            raise SkipTest("Sessions not supported")

        if not env.is_replica_set:
            raise SkipTest("Requires a replica set")

        if env.version < Version(3, 7):
            raise SkipTest("Requires MongoDB 3.7+")

    def transaction_test_debug(self, msg):
        if _TXN_TESTS_DEBUG:
            print(msg)

    def check_result(self, expected_result, result):
        write_results = (BulkWriteResult,
                         DeleteResult,
                         InsertOneResult,
                         InsertManyResult,
                         UpdateResult)

        if isinstance(result, write_results):
            for res in expected_result:
                prop = camel_to_snake(res)
                # SPEC-869: Only BulkWriteResult has upserted_count.
                if (prop == "upserted_count"
                        and not isinstance(result, BulkWriteResult)):
                    if result.upserted_id is not None:
                        upserted_count = 1
                    else:
                        upserted_count = 0
                    self.assertEqual(upserted_count, expected_result[res], prop)
                elif prop == "inserted_ids":
                    # BulkWriteResult does not have inserted_ids.
                    if isinstance(result, BulkWriteResult):
                        self.assertEqual(len(expected_result[res]),
                                         result.inserted_count)
                    else:
                        # InsertManyResult may be compared to [id1] from the
                        # crud spec or {"0": id1} from the retryable write spec.
                        ids = expected_result[res]
                        if isinstance(ids, dict):
                            ids = [ids[str(i)] for i in range(len(ids))]
                        self.assertEqual(ids, result.inserted_ids, prop)
                elif prop == "upserted_ids":
                    # Convert indexes from strings to integers.
                    ids = expected_result[res]
                    expected_ids = {}
                    for str_index in ids:
                        expected_ids[int(str_index)] = ids[str_index]
                    self.assertEqual(expected_ids, result.upserted_ids, prop)
                else:
                    self.assertEqual(
                        getattr(result, prop), expected_result[res], prop)

            return True
        elif isinstance(result, dict):
            for k, v in expected_result.items():
                self.assertEqual(v, result[k])
        else:
            self.assertEqual(expected_result, result)

    @gen.coroutine
    def run_operation(self, sessions, collection, operation):
        name = camel_to_snake(operation['name'])
        if name == 'run_command':
            name = 'command'

        self.transaction_test_debug(name)

        collection_opts = operation.get('collectionOptions')
        if collection_opts:
            collection = collection.with_options(**parse_opts(collection_opts))

        obj = {
            'collection': collection,
            'database': collection.database,
            'session0': sessions['session0'],
            'session1': sessions['session1'],
        }[operation['object']]

        # Combine arguments with options and handle special cases.
        arguments = operation['arguments']
        arguments.update(arguments.pop("options", {}))
        kwargs = parse_args(arguments, sessions)

        for arg_name, arg_value in arguments.items():
            c2s = camel_to_snake(arg_name)
            if arg_name == "sort":
                assert len(arg_value) == 1, 'test can only have 1 sort key'
                kwargs[arg_name] = list(arg_value.items())
            # Named "key" instead not fieldName.
            elif arg_name == "fieldName":
                kwargs["key"] = arg_value
            # Aggregate uses "batchSize", while find uses batch_size.
            elif arg_name == "batchSize" and name == "aggregate":
                kwargs["batchSize"] = arg_value
            # Requires boolean returnDocument.
            elif arg_name == "returnDocument":
                kwargs[c2s] = (arg_value == "After")
            elif c2s == "requests":
                # Parse each request into a bulk write model.
                requests = []
                for request in arg_value:
                    bulk_model = camel_to_upper_camel(request["name"])
                    bulk_class = getattr(operations, bulk_model)
                    bulk_arguments = camel_to_snake_args(request["arguments"])
                    requests.append(bulk_class(**bulk_arguments))
                kwargs["requests"] = requests
            else:
                kwargs[c2s] = arg_value

        cmd = getattr(obj, name)
        result = cmd(**kwargs)
        try:
            result = gen.convert_yielded(result)
        except gen.BadYieldError:
            # Not an async method.
            pass
        else:
            result = yield result

        cursor_types = MotorCursor, MotorCommandCursor, MotorLatentCommandCursor
        if isinstance(result, cursor_types):
            result = yield result.to_list(length=None)

        raise gen.Return(result)

    def check_events(self, test, listener, session_ids):
        res = listener.results
        if not len(test['expectations']):
            return

        self.assertEqual(len(res['started']), len(test['expectations']))
        for i, expectation in enumerate(test['expectations']):
            event_type = next(iter(expectation))
            event = res['started'][i]

            # The tests substitute 42 for any number other than 0.
            if (event.command_name == 'getMore'
                and event.command['getMore']):
                event.command['getMore'] = 42
            elif event.command_name == 'killCursors':
                event.command['cursors'] = [42]

            # Replace afterClusterTime: 42 with actual afterClusterTime.
            expected_cmd = expectation[event_type]['command']
            expected_read_concern = expected_cmd.get('readConcern')
            if expected_read_concern is not None:
                time = expected_read_concern.get('afterClusterTime')
                if time == 42:
                    actual_time = event.command.get(
                        'readConcern', {}).get('afterClusterTime')
                    if actual_time is not None:
                        expected_read_concern['afterClusterTime'] = actual_time

            # Replace lsid with a name like "session0" to match test.
            if 'lsid' in event.command:
                for name, lsid in session_ids.items():
                    if event.command['lsid'] == lsid:
                        event.command['lsid'] = name
                        break

            for attr, expected in expectation[event_type].items():
                actual = getattr(event, attr)
                if isinstance(expected, dict):
                    for key, val in expected.items():
                        if val is None:
                            if key in actual:
                                self.fail("Unexpected key [%s] in %r" % (
                                    key, actual))
                        elif key not in actual:
                            self.fail("Expected key [%s] in %r" % (
                                key, actual))
                        else:
                            self.assertEqual(val, actual[key],
                                             "Key [%s] in %s" % (key, actual))
                else:
                    self.assertEqual(actual, expected)


def expect_error(expected_result):
    if isinstance(expected_result, dict):
        return set(expected_result.keys()).intersection((
            'errorContains', 'errorCodeName', 'errorLabelsContain',
            'errorLabelsOmit'))

    return False


def end_sessions(sessions):
    for s in sessions.values():
        # Aborts the transaction if it's open.
        s.end_session()


def create_test(scenario_def, test):
    @gen_test
    def run_scenario(self):
        listener = OvertCommandListener()
        # New client, to avoid interference from pooled sessions.
        client = self.motor_rsc(event_listeners=[listener],
                                **test['clientOptions'])
        try:
            yield client.admin.command('killAllSessions', [])
        except OperationFailure:
            # "operation was interrupted" by killing the command's own session.
            pass

        if test['failPoint']:
            yield client.admin.command(test['failPoint'])

        database_name = scenario_def['database_name']
        collection_name = scenario_def['collection_name']
        write_concern_db = client.get_database(
            database_name, write_concern=WriteConcern(w='majority'))
        write_concern_coll = write_concern_db[collection_name]
        yield write_concern_coll.drop()
        yield write_concern_db.create_collection(collection_name)
        if scenario_def['data']:
            # Load data.
            yield write_concern_coll.insert_many(scenario_def['data'])

        # Create session0 and session1.
        sessions = {}
        session_ids = {}
        for i in range(2):
            session_name = 'session%d' % i
            opts = camel_to_snake_args(test['sessionOptions'][session_name])
            if 'default_transaction_options' in opts:
                txn_opts = opts['default_transaction_options']
                if 'readConcern' in txn_opts:
                    read_concern = ReadConcern(**txn_opts['readConcern'])
                else:
                    read_concern = None
                if 'writeConcern' in txn_opts:
                    write_concern = WriteConcern(**txn_opts['writeConcern'])
                else:
                    write_concern = None

                if 'readPreference' in txn_opts:
                    read_pref = parse_read_preference(
                        txn_opts['readPreference'])
                else:
                    read_pref = None

                txn_opts = client_session.TransactionOptions(
                    read_concern=read_concern,
                    write_concern=write_concern,
                    read_preference=read_pref,
                )
                opts['default_transaction_options'] = txn_opts

            s = yield client.start_session(**opts)

            sessions[session_name] = s
            # Store lsid so we can access it after end_session, in check_events.
            session_ids[session_name] = s.session_id

        self.addCleanup(end_sessions, sessions)

        listener.results.clear()
        collection = client[database_name][collection_name]

        for op in test['operations']:
            expected_result = op.get('result')
            if expect_error(expected_result):
                with self.assertRaises(PyMongoError,
                                       msg=op.get('name')) as context:
                    yield self.run_operation(sessions, collection, op.copy())

                err = context.exception
                if expected_result['errorContains']:
                    self.assertIn(expected_result['errorContains'].lower(),
                                  str(err).lower())

                if expected_result['errorCodeName']:
                    self.assertEqual(expected_result['errorCodeName'],
                                     err.details.get('codeName'))

                for label in expected_result.get('errorLabelsContain', []):
                    self.assertTrue(
                        err.has_error_label(label),
                        "%r should have errorLabel %s" % (err, label))

                for label in expected_result.get('errorLabelsOmit', []):
                    self.assertFalse(
                        err.has_error_label(label),
                        "%r should NOT have errorLabel %s" % (err, label))
            else:
                result = yield self.run_operation(
                    sessions, collection, op.copy())
                if 'result' in op:
                    self.check_result(expected_result, result)

        for s in sessions.values():
            yield s.end_session()

        self.check_events(test, listener, session_ids)

        # Assert final state is expected.
        expected = test['outcome'].get('collection')
        if expected is not None:
            # Read from the primary to ensure causal consistency.
            primary_coll = collection.with_options(
                read_preference=ReadPreference.PRIMARY)
            docs = yield primary_coll.find().to_list(length=None)
            self.assertEqual(expected['data'], docs)

    return run_scenario


class ScenarioDict(collections.OrderedDict):
    """Dict that returns {} for any unknown key, recursively."""

    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            # Unlike a defaultdict, don't set the key, just return a dict.
            return ScenarioDict({})

    def copy(self):
        return ScenarioDict(self)


def create_tests():
    assert os.path.isdir(_TEST_PATH)
    for dirpath, _, filenames in os.walk(_TEST_PATH):
        dirname = os.path.split(dirpath)[-1]

        for filename in filenames:
            test_type, ext = os.path.splitext(filename)
            if ext != '.json':
                continue

            with open(os.path.join(dirpath, filename)) as scenario_stream:
                opts = JSONOptions(document_class=ScenarioDict)
                scenario_def = json_util.loads(
                    scenario_stream.read(), json_options=opts)

            # Construct test from scenario.
            for test in scenario_def['tests']:
                test_name = 'test_%s_%s_%s' % (
                    dirname,
                    test_type.replace("-", "_"),
                    str(test['description'].replace(" ", "_")))

                new_test = create_test(scenario_def, test)
                new_test = env.require(
                    lambda: not test.get('skipReason'),
                    test.get('skipReason'),
                    new_test)

                if test_type == 'reads' and test['description'] == 'count':
                    new_test = env.require(
                        lambda: False,
                        "Motor has removed the 'count' helper",
                        new_test)

                if 'secondary' in test_name:
                    new_test = env.require(
                        lambda: env.secondaries,
                        'No secondaries',
                        new_test)

                # In Python 2, case test_name from unicode to str.
                new_test.__name__ = str(test_name)
                setattr(MotorTransactionTest, new_test.__name__, new_test)


create_tests()

if __name__ == '__main__':
    unittest.main()
