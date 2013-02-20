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

"""Utilities for testing Motor
"""

def one(s):
    """Get one element of a set"""
    return iter(s).next()

def delay(sec):
    # Javascript sleep() available in MongoDB since version ~1.9
    return 'sleep(%s * 1000); return true' % sec

def get_command_line(connection):
    command_line = connection.admin.command('getCmdLineOpts')
    assert command_line['ok'] == 1, "getCmdLineOpts() failed"
    return command_line['argv']

def server_started_with_auth(connection):
    argv = get_command_line(connection)
    return '--auth' in argv or '--keyFile' in argv

def server_is_master_with_slave(connection):
    return '--master' in get_command_line(connection)
