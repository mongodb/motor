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

from __future__ import unicode_literals, absolute_import

"""Common code to support all async frameworks."""

import pymongo.errors


callback_type_error = TypeError("callback must be a callable")


def check_deprecated_kwargs(kwargs):
    if 'safe' in kwargs:
        raise pymongo.errors.ConfigurationError(
            "Motor does not support 'safe', use 'w'")

    if 'slave_okay' in kwargs or 'slaveok' in kwargs:
        raise pymongo.errors.ConfigurationError(
            "Motor does not support 'slave_okay', use read_preference")

    if 'auto_start_request' in kwargs:
        raise pymongo.errors.ConfigurationError(
            "Motor does not support requests")


def mangle_delegate_name(motor_class, name):
    if name.startswith('__') and not name.endswith("__"):
        # Mangle, e.g. Cursor.__die -> Cursor._Cursor__die
        classname = motor_class.__delegate_class__.__name__
        return '_%s%s' % (classname, name)
    else:
        return name


class MotorSocketOptions(object):
    def __init__(
        self,
        resolver,
        address,
        family,
        use_ssl,
        certfile,
        keyfile,
        ca_certs,
        cert_reqs,
        socket_keepalive
    ):
        self.resolver = resolver
        self.address = address
        self.family = family
        self.use_ssl = use_ssl
        self.certfile = certfile
        self.keyfile = keyfile
        self.ca_certs = ca_certs
        self.cert_reqs = cert_reqs
        self.socket_keepalive = socket_keepalive
