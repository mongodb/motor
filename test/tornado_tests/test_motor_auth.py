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

from pymongo.errors import OperationFailure
from tornado.testing import gen_test

from test.test_environment import env
from test.tornado_tests import MotorTest

"""Test Motor, an asynchronous driver for MongoDB and Tornado."""


class MotorAuthTest(MotorTest):
    @env.require_auth
    @env.require_version_min(4, 0)
    def setUp(self):
        super().setUp()
        self._reset()

    def tearDown(self):
        self._reset()

    def _reset(self):
        env.sync_cx.scramtestdb.command("dropAllUsersFromDatabase")
        env.sync_cx.drop_database("scramtestdb")

    @gen_test
    async def test_scram(self):
        env.create_user('scramtestdb',
                        'sha1',
                        'pwd',
                        roles=['dbOwner'],
                        mechanisms=['SCRAM-SHA-1'])

        env.create_user('scramtestdb',
                        'sha256',
                        'pwd',
                        roles=['dbOwner'],
                        mechanisms=['SCRAM-SHA-256'])

        env.create_user('scramtestdb',
                        'both',
                        'pwd',
                        roles=['dbOwner'],
                        mechanisms=['SCRAM-SHA-1', 'SCRAM-SHA-256'])

        for user, mechanism, should_work in [('sha1', 'SCRAM-SHA-1', True),
                                             ('sha1', 'SCRAM-SHA-256', False),
                                             ('sha256', 'SCRAM-SHA-256', True),
                                             ('sha256', 'SCRAM-SHA-1', False),
                                             ('both', 'SCRAM-SHA-1', True),
                                             ('both', 'SCRAM-SHA-256', True)]:
            client = self.motor_client(username=user,
                                       password='pwd',
                                       authsource='scramtestdb',
                                       authmechanism=mechanism)

            if should_work:
                await client.scramtestdb.collection.insert_one({})
            else:
                with self.assertRaises(OperationFailure):
                    await client.scramtestdb.collection.insert_one({})

        # No mechanism specified, always works.
        for user, mechanism, should_work in [('sha1', None, True),
                                             ('sha256', None, False),
                                             ('both', None, True)]:
            client = self.motor_client(username=user,
                                       password='pwd',
                                       authsource='scramtestdb')

            await client.scramtestdb.collection.insert_one({})

    @gen_test
    async def test_saslprep(self):
        # Use Roman numeral for password, normalized by SASLprep to ASCII "IV",
        # see RFC 4013. MongoDB SASL mech normalizes password only, not user.
        env.create_user('scramtestdb',
                        'saslprep-test-user',
                        u'\u2163',
                        roles=['dbOwner'],
                        mechanisms=['SCRAM-SHA-256'])

        client = self.motor_client(username='saslprep-test-user',
                                   password='IV',
                                   authsource='scramtestdb')

        await client.scramtestdb.collection.insert_one({})
