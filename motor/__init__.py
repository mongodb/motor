# Copyright 2011-2015 MongoDB, Inc.
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

"""Motor, an asynchronous driver for MongoDB."""

from __future__ import unicode_literals, absolute_import

import pymongo

from motor.motor_py3_compat import text_type

version_tuple = (0, 5)


def get_version_string():
    if isinstance(version_tuple[-1], text_type):
        return '.'.join(map(str, version_tuple[:-1])) + version_tuple[-1]
    return '.'.join(map(str, version_tuple))

version = get_version_string()
"""Current version of Motor."""

expected_pymongo_version = '2.8'
if pymongo.version != expected_pymongo_version:
    msg = (
        "Motor %s requires PyMongo at exactly version %s. "
        "You have PyMongo %s. "
        "Do pip install pymongo==2.8.0"
    ) % (version, expected_pymongo_version, pymongo.version)

    raise ImportError(msg)

try:
    import tornado
except ImportError:
    tornado = None
else:
    # For backwards compatibility with Motor 0.4, export Motor's Tornado classes
    # at module root. This may change in Motor 1.0. First get __all__.
    from .motor_tornado import *

    # Now some classes that aren't in __all__ but might be expected.
    from .motor_tornado import (MotorCollection,
                                MotorDatabase,
                                MotorGridFS,
                                MotorGridIn,
                                MotorGridOut,
                                MotorBulkOperationBuilder)

    # Make "from motor import *" the same as "from motor.motor_tornado import *"
    from .motor_tornado import __all__
