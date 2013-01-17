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

from docutils.nodes import field, list_item, paragraph, title_reference
from docutils.nodes import field_list, field_body, bullet_list, Text, field_name
from sphinx.addnodes import desc, desc_content, versionmodified, desc_signature
from sphinx.util.inspect import safe_getattr

import motor


# This is a place to store info while parsing, to be used before generating.
motor_info = {}


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
    #
    # We do this here, rather than by registering a callback to Sphinx's
    # 'autodoc-process-signature' event, because it's way easier to handle the
    # parsed doctree before it's turned into HTML than it is to update the RST.
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
                        parameters_node, obj_motor_info['callback_required'])

                if obj_motor_info['is_pymongo_docstring']:
                    # Remove all "versionadded", "versionchanged" and
                    # "deprecated" directives from the docs we imported from
                    # PyMongo
                    version_nodes = find_by_path(
                        desc_content_node, [versionmodified])

                    for version_node in version_nodes:
                        version_node.parent.remove(version_node)


def get_motor_attr(motor_class, name, *defargs):
    """If any Motor attributes can't be accessed, grab the equivalent PyMongo
    attribute. While we're at it, store some info about each attribute
    in the global motor_info dict.
    """
    from_pymongo = False
    try:
        attr = safe_getattr(motor_class, name, *defargs)
    except AttributeError:
        # Typically, this means 'name' is refers not to an async method like
        # MotorDatabase.command, but to a ReadOnlyProperty, e.g.
        # MotorClient.close(). The latter can't be accessed directly, but we
        # can get the docstring and method signature from the equivalent
        # PyMongo attribute, e.g. pymongo.mongo_client.MongoClient.close().
        attr = getattr(motor_class.__delegate_class__, name, *defargs)
        from_pymongo = True

    # Store some info for process_motor_nodes()
    full_name = '%s.%s.%s' % (
        motor_class.__module__, motor_class.__name__, name)

    is_async_method = getattr(attr, 'is_async_method', False)
    motor_info[full_name] = {
        # These sub-attributes are set in motor.asynchronize()
        'is_async_method': is_async_method,
        'callback_required': getattr(attr, 'callback_required', False),
        'is_pymongo_docstring': from_pymongo or is_async_method}

    return attr


def setup(app):
    app.add_autodoc_attrgetter(type(motor.MotorBase), get_motor_attr)
    app.connect("doctree-read", process_motor_nodes)
