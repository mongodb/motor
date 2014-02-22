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

"""Utilities for testing Motor
"""

from tornado import gen
from nose.plugins.skip import SkipTest

from test import version


def one(s):
    """Get one element of a set"""
    return iter(s).next()


def delay(sec):
    # Javascript sleep() available in MongoDB since version ~1.9
    return 'sleep(%s * 1000); return true' % sec


@gen.coroutine
def get_command_line(client):
    command_line = yield client.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    raise gen.Return(command_line['argv'])


@gen.coroutine
def server_started_with_auth(client):
    argv = yield get_command_line(client)
    raise gen.Return('--auth' in argv or '--keyFile' in argv)


@gen.coroutine
def server_is_master_with_slave(client):
    command_line = yield get_command_line(client)
    raise gen.Return('--master' in command_line)


@gen.coroutine
def server_is_mongos(client):
    ismaster_response = yield client.admin.command('ismaster')
    raise gen.Return(ismaster_response.get('msg') == 'isdbgrid')


@gen.coroutine
def skip_if_mongos(client):
    is_mongos = yield server_is_mongos(client)
    if is_mongos:
        raise SkipTest("connected to mongos")


@gen.coroutine
def remove_all_users(db):
    version_check = yield version.at_least(db.connection, (2, 5, 4))
    if version_check:
        yield db.command({"dropAllUsersFromDatabase": 1})
    else:
        yield db.system.users.remove({})
