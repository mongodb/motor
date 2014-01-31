# Copyright 2009-2014 MongoDB, Inc.
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

"""Some tools for running tests based on MongoDB server version."""

from tornado import gen


def _padded(iter, length, padding=0):
    l = list(iter)
    if len(l) < length:
        for _ in range(length - len(l)):
            l.append(0)
    return l


def _parse_version_string(version_string):
    mod = 0
    if version_string.endswith("+"):
        version_string = version_string[0:-1]
        mod = 1
    elif version_string.endswith("-pre-"):
        version_string = version_string[0:-5]
        mod = -1
    elif version_string.endswith("-"):
        version_string = version_string[0:-1]
        mod = -1
    # Deal with '-rcX' substrings
    if version_string.find('-rc') != -1:
        version_string = version_string[0:version_string.find('-rc')]
        mod = -1

    version = [int(part) for part in version_string.split(".")]
    version = _padded(version, 3)
    version.append(mod)

    return tuple(version)


@gen.coroutine
def version(client):
    info = yield client.server_info()
    raise gen.Return(_parse_version_string(info["version"]))


@gen.coroutine
def at_least(client, min_version):
    client_version = yield version(client)
    raise gen.Return(client_version >= tuple(_padded(min_version, 4)))
