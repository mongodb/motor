# Copyright 2009-2016 MongoDB, Inc.
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

from __future__ import unicode_literals, absolute_import

"""Some tools for running tests based on MongoDB server version."""

import re


def padded(iter, length):
    l = list(iter)
    if len(l) < length:
        for _ in range(length - len(l)):
            l.append(0)
    return l


def _parse_version_string(version_string):
    match = re.match(r'(\d+\.\d+\.\d+).*', version_string)
    assert match, "Couldn't parse server version %s" % version_string
    version = [int(part) for part in match.group(1).split(".")]
    mod = 0
    if version_string.endswith("+"):
        mod = 1
    elif version_string.endswith("-pre-"):
        mod = -1
    elif version_string.endswith("-"):
        mod = -1
    elif version_string.find('-rc') != -1:
        mod = -1
    elif re.match(r'\d+\.\d+\.\d+-\d+-g[0-9a-fA-F]+', version_string):
        # Like '3.3.10-421-gbd66e1b'.
        mod = 1

    version = padded(version, 3)
    version.append(mod)

    return tuple(version)
