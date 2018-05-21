# Copyright 2011-present MongoDB, Inc.
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

version_tuple = (1, 2, 2)


def get_version_string():
    return '.'.join(map(str, version_tuple))


version = get_version_string()
"""Current version of Motor."""

pymongo_required = 3, 4
if pymongo.version_tuple[:2] < pymongo_required:
    major, minor = pymongo_required
    msg = (
        "Motor %s requires PyMongo %s.%s or later. "
        "You have PyMongo %s. "
        "Do python -m pip install \"pymongo>=%s.%s,<4\""
    ) % (version,
         major, minor,
         pymongo.version,
         major, minor)

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
                                MotorGridFSBucket,
                                MotorGridIn,
                                MotorGridOut,
                                MotorBulkOperationBuilder)

    # Make "from motor import *" the same as "from motor.motor_tornado import *"
    from .motor_tornado import __all__
