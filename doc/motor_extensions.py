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

"""Motor specific extensions to Sphinx."""

import inspect

from docutils.nodes import field, list_item, paragraph, title_reference
from docutils.nodes import field_list, field_body, bullet_list, Text, field_name
from sphinx.addnodes import desc, desc_content, versionmodified, desc_signature
from sphinx.addnodes import desc_name
from sphinx.util.inspect import getargspec, safe_getattr
from sphinx.ext.autodoc import MethodDocumenter, AttributeDocumenter

import motor


# TODO: HACK! This is a place to store info while parsing, to be used before
#   generating
motor_info = {}


class MotorAttribute(object):
    def __init__(self, motor_class, name, delegate_property):
        super(MotorAttribute, self).__init__()
        self.motor_class = motor_class
        self.name = name
        self.delegate_property = delegate_property
        self.pymongo_attr = getattr(motor_class.__delegate_class__, name)

        # Store some info for process_motor_nodes()
        full_name = '%s.%s.%s' % (
            self.motor_class.__module__, self.motor_class.__name__,
            self.name)

        motor_info[full_name] = {
            'is_async_method': self.is_async_method(),
            'requires_callback': self.requires_callback(),
        }

    def is_async_method(self):
        return isinstance(self.delegate_property, motor.Async)

    def requires_callback(self):
        return self.is_async_method() and self.delegate_property.cb_required

    @property
    def __doc__(self):
        return self.pymongo_attr.__doc__ or ''

    def getargspec(self):
        args, varargs, kwargs, defaults = getargspec(self.pymongo_attr)

        # This part is copied from Sphinx's autodoc.py
        if args and args[0] in ('cls', 'self'):
            del args[0]

        # Add 'callback=None' argument
        defaults = defaults or []
        prop = self.delegate_property
        if isinstance(prop, motor.Async):
            args.append('callback')
            defaults.append(None)

        return (args, varargs, kwargs, defaults)

    def format_args(self):
        if self.is_async_method():
            return inspect.formatargspec(*self.getargspec())
        else:
            return None


def get_pymongo_attr(obj, name, *defargs):
    """getattr() override for Motor DelegateProperty."""
    if isinstance(obj, motor.MotorMeta):
        for cls in inspect.getmro(obj):
            if name in cls.__dict__:
                attr = cls.__dict__[name]
                if isinstance(attr, motor.DelegateProperty):
                    # 'name' set by MotorMeta
                    assert attr.get_name() == name, (
                        "Expected name %s, got %s" % (name, attr.get_name()))
                    return MotorAttribute(obj, name, attr)
    return safe_getattr(obj, name, *defargs)


class MotorMethodDocumenter(MethodDocumenter):
    objtype = 'motormethod'
    directivetype = 'method'

    @staticmethod
    def get_attr(obj, name, *defargs):
        return get_pymongo_attr(obj, name, *defargs)

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, motor.Async)

    def format_args(self):
        assert isinstance(self.object, MotorAttribute), (
            "%s is not a motor.Async, just use 'automethod', not"
            " 'automotormethod'" % self.object)
        return self.object.format_args()


class MotorAttributeDocumenter(AttributeDocumenter):
    objtype = 'motorattribute'
    directivetype = 'attribute'

    @staticmethod
    def get_attr(obj, name, *defargs):
        return get_pymongo_attr(obj, name, *defargs)

    def import_object(self):
        # Convince AttributeDocumenter that this is a data descriptor
        ret = super(MotorAttributeDocumenter, self).import_object()
        self._datadescriptor = True
        return ret

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return isinstance(member, motor.DelegateProperty)


def find_by_path(root, classes):
    if not classes:
        return [root]

    _class = classes[0]
    rv = []
    for child in root.children:
        if isinstance(child, _class):
            rv.extend(find_by_path(child, classes[1:]))

    return rv


def get_parameter_names(parameters_node):
    parameter_names = []
    for title_ref_node in find_by_path(parameters_node,
        [list_item, paragraph, title_reference]
    ):
        parameter_names.append(title_ref_node[0].astext())

    return parameter_names


def insert_callback(parameters_node, callback_required):
    # We need to know what params are here already
    parameter_names = get_parameter_names(parameters_node)

    if 'callback' not in parameter_names:
        if '*args' in parameter_names:
            args_pos = parameter_names.index('*args')
        else:
            args_pos = len(parameter_names)

        if '**kwargs' in parameter_names:
            kwargs_pos = parameter_names.index('**kwargs')
        else:
            kwargs_pos = len(parameter_names)

        doc = (": function taking (result, error), to execute when operation"
            " completes")

        if not callback_required:
            doc = " (optional)" + doc

        new_item = list_item(
            '', paragraph(
                '', '',
                title_reference('', 'callback'),
                Text(doc)))

        # Insert "callback" before *args and **kwargs
        parameters_node.insert(min(args_pos, kwargs_pos), new_item)


def process_motor_nodes(app, doctree):
    # Search doctree for Motor's methods and attributes whose docstrings were
    # copied from PyMongo, and fix them up for Motor:
    #   1. Add a 'callback' param (sometimes optional, sometimes required) to
    #      all async methods. If the PyMongo method took no params, we create
    #      a parameter-list from scratch, otherwise we edit PyMongo's list.
    #   2. Remove all version annotations like "New in version 2.0" since
    #      PyMongo's version numbers are meaningless in Motor's docs.
    for objnode in doctree.traverse(desc):
        if objnode['objtype'] in ('method', 'attribute'):
            signature_node = find_by_path(objnode, [desc_signature])[0]
            name = '.'.join([
                signature_node['module'], signature_node['fullname']])

            assert name.startswith('motor.')
            obj_motor_info = motor_info.get(name)
            if obj_motor_info:
                desc_content_node = find_by_path(objnode, [desc_content])[0]
                if obj_motor_info.get('is_async_method'):
                    try:
                        # Find the parameter list, a bullet_list instance
                        parameters_node = find_by_path(desc_content_node,
                            [field_list, field, field_body, bullet_list])[0]
                    except IndexError:
                        # PyMongo method has no parameters, create an empty
                        # params list
                        parameters_node = bullet_list()
                        parameters_field_list_node = field_list('',
                            field('',
                                field_name('', 'Parameters '),
                                field_body('',
                                    parameters_node)))

                        desc_content_node.append(parameters_field_list_node)

                    insert_callback(
                        parameters_node, obj_motor_info['requires_callback'])

                # Remove all "versionadded", "versionchanged" and "deprecated"
                # directives from the docs we imported from PyMongo
                version_nodes = find_by_path(desc_content_node, [versionmodified])
                for version_node in version_nodes:
                    version_node.parent.remove(version_node)


def setup(app):
    app.add_autodocumenter(MotorMethodDocumenter)
    app.add_autodocumenter(MotorAttributeDocumenter)
    app.connect("doctree-read", process_motor_nodes)
