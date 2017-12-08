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

"""Motor specific extensions to Sphinx."""

import inspect
import re
from itertools import chain

from docutils.nodes import field, list_item, paragraph, title_reference, literal
from docutils.nodes import field_list, field_body, bullet_list, Text, field_name
from docutils.nodes import literal_block, doctest_block
from sphinx import addnodes
from sphinx.addnodes import (desc, desc_content, versionmodified,
                             desc_signature, seealso, pending_xref)
from sphinx.util.inspect import safe_getattr

import motor
import motor.core


# This is a place to store info while parsing, to be used before generating.
motor_info = {}


def is_asyncio_api(name):
    return 'motor_asyncio.' in name


def has_node_of_type(root, klass):
    if isinstance(root, klass):
        return True

    for child in root.children:
        if has_node_of_type(child, klass):
            return True

    return False


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

    # Most PyMongo methods have bullet lists.
    for list_item_node in find_by_path(parameters_node, [list_item]):
        title_ref_nodes = find_by_path(
            list_item_node, [paragraph, (title_reference, pending_xref)])

        parameter_names.append(title_ref_nodes[0].astext())

    # Some are just paragraphs.
    for title_ref_node in find_by_path(parameters_node, [title_reference]):
        parameter_names.append(title_ref_node.astext())

    return parameter_names


def insert_callback(parameters_node):
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

        doc = (
            " (optional): function taking (result, error), executed when"
            " operation completes")

        new_item = paragraph(
            '', '',
            literal('', 'callback'),
            Text(doc))

        if parameters_node.children and isinstance(parameters_node.children[0],
                                                   list_item):
            # Insert "callback" before *args and **kwargs
            parameters_node.insert(min(args_pos, kwargs_pos),
                                   list_item('', new_item))
        else:
            parameters_node.append(new_item)


docstring_warnings = []


def maybe_warn_about_code_block(name, content_node):
    if has_node_of_type(content_node, (literal_block, doctest_block)):
        docstring_warnings.append(name)


def has_coro_annotation(signature_node):
    try:
        return 'coroutine' in signature_node[0][0]
    except IndexError:
        return False


def process_motor_nodes(app, doctree):
    # Search doctree for Motor's methods and attributes whose docstrings were
    # copied from PyMongo, and fix them up for Motor:
    #   1. Add a 'callback' param (sometimes optional, sometimes required) to
    #      all Motor Tornado methods. If the PyMongo method took no params, we
    #      create a parameter-list from scratch, otherwise we edit PyMongo's
    #      list.
    #   2. Remove all version annotations like "New in version 2.0" since
    #      PyMongo's version numbers are meaningless in Motor's docs.
    #   3. Remove "seealso" directives that reference PyMongo's docs.
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
                if (desc_content_node.line is None and
                        obj_motor_info['is_pymongo_docstring']):
                    maybe_warn_about_code_block(name, desc_content_node)

                if obj_motor_info['is_async_method']:
                    # Might be a handwritten RST with "coroutine" already.
                    if not has_coro_annotation(signature_node):
                        coro_annotation = addnodes.desc_annotation(
                            'coroutine ', 'coroutine ',
                            classes=['coro-annotation'])

                        signature_node.insert(0, coro_annotation)

                    if (not is_asyncio_api(name)
                            and obj_motor_info['coroutine_has_callback']):
                        retval = ("If a callback is passed, returns None, else"
                                  " returns a Future.")

                        callback_p = paragraph('', Text(retval))

                        # Find the parameter list.
                        parameters_nodes = find_by_path(
                            desc_content_node, [
                                field_list,
                                field,
                                field_body,
                                (bullet_list, paragraph)])

                        if parameters_nodes:
                            parameters_node = parameters_nodes[0]
                        else:
                            # PyMongo method has no parameters, create an empty
                            # params list
                            parameters_node = bullet_list()
                            parameters_field_list_node = field_list(
                                '',
                                field(
                                    '',
                                    field_name('', 'Parameters '),
                                    field_body('', parameters_node)))
                            desc_content_node.append(parameters_field_list_node)

                        insert_callback(parameters_node)
                        if retval not in str(desc_content_node):
                            desc_content_node.append(callback_p)

                if obj_motor_info['is_pymongo_docstring']:
                    # Remove all "versionadded", "versionchanged" and
                    # "deprecated" directives from the docs we imported from
                    # PyMongo
                    version_nodes = find_by_path(
                        desc_content_node, [versionmodified])

                    for version_node in version_nodes:
                        version_node.parent.remove(version_node)

                    # Remove all "seealso" directives that contain :doc:
                    # references from PyMongo's docs
                    seealso_nodes = find_by_path(desc_content_node, [seealso])

                    for seealso_node in seealso_nodes:
                        if 'reftype="doc"' in str(seealso_node):
                            seealso_node.parent.remove(seealso_node)


def get_motor_attr(motor_class, name, *defargs):
    """If any Motor attributes can't be accessed, grab the equivalent PyMongo
    attribute. While we're at it, store some info about each attribute
    in the global motor_info dict.
    """
    attr = safe_getattr(motor_class, name)

    # Store some info for process_motor_nodes()
    full_name = '%s.%s.%s' % (
        motor_class.__module__, motor_class.__name__, name)

    full_name_legacy = 'motor.%s.%s.%s' % (
        motor_class.__module__, motor_class.__name__, name)

    # These sub-attributes are set in motor.asynchronize()
    has_coroutine_annotation = getattr(attr, 'coroutine_annotation', False)
    is_async_method = getattr(attr, 'is_async_method', False)
    coroutine_has_callback = has_coroutine_annotation or is_async_method
    if has_coroutine_annotation:
        coroutine_has_callback = getattr(attr, 'coroutine_has_callback', True)
    is_cursor_method = getattr(attr, 'is_motorcursor_chaining_method', False)
    if is_async_method or is_cursor_method:
        pymongo_method = getattr(
            motor_class.__delegate_class__, attr.pymongo_method_name)
    else:
        pymongo_method = None

    # attr.doc is set by statement like 'error = AsyncRead(doc="OBSOLETE")'.
    is_pymongo_doc = pymongo_method and attr.__doc__ == pymongo_method.__doc__

    motor_info[full_name] = motor_info[full_name_legacy] = {
        'is_async_method': is_async_method or has_coroutine_annotation,
        'coroutine_has_callback': coroutine_has_callback,
        'is_pymongo_docstring': is_pymongo_doc,
        'pymongo_method': pymongo_method,
    }

    return attr


def get_motor_argspec(name, method):
    args, varargs, kwargs, defaults = inspect.getargspec(method)

    # This part is copied from Sphinx's autodoc.py
    if args and args[0] in ('cls', 'self'):
        del args[0]

    defaults = list(defaults) if defaults else []
    add_callback = True
    if 'callback' in chain(args or [], kwargs or []):
        add_callback = False
    elif is_asyncio_api(name):
        add_callback = False
    elif (getattr(method, 'coroutine_annotation', False)
          and not getattr(method, 'coroutine_has_callback', True)):
        add_callback = False

    if add_callback:
        # Add 'callback=None' argument
        args.append('callback')
        defaults.append(None)

    return args, varargs, kwargs, defaults


# Adapted from MethodDocumenter.format_args
def format_motor_args(name, motor_method, pymongo_method):
    if pymongo_method:
        argspec = get_motor_argspec(name, pymongo_method)
    else:
        argspec = get_motor_argspec(name, motor_method)

    formatted_argspec = inspect.formatargspec(*argspec)
    # escape backslashes for reST
    return formatted_argspec.replace('\\', '\\\\')


pymongo_ref_pat = re.compile(r':doc:`(.*?)`', re.MULTILINE)


def _sub_pymongo_ref(match):
    ref = match.group(1)
    return ':doc:`%s`' % ref.lstrip('/')


def process_motor_docstring(app, what, name, obj, options, lines):
    if name in motor_info and motor_info[name].get('is_pymongo_docstring'):
        joined = '\n'.join(lines)
        subbed = pymongo_ref_pat.sub(_sub_pymongo_ref, joined)
        lines[:] = subbed.split('\n')


def process_motor_signature(
        app, what, name, obj, options, signature, return_annotation):
    info = motor_info.get(name)
    if info:
        # Real sig obscured by decorator, reconstruct it
        pymongo_method = info['pymongo_method']
        if info['is_async_method']:
            args = format_motor_args(name, obj, pymongo_method)
            return args, return_annotation


def build_finished(app, exception):
    if not exception and docstring_warnings:
        print("PyMongo docstrings with code blocks that need update:")
        for name in sorted(docstring_warnings):
            print(name)


def setup(app):
    app.add_autodoc_attrgetter(type(motor.core.AgnosticBase), get_motor_attr)
    app.connect('autodoc-process-docstring', process_motor_docstring)
    app.connect('autodoc-process-signature', process_motor_signature)
    app.connect('doctree-read', process_motor_nodes)
    app.connect('build-finished', build_finished)
    return {'parallel_write_safe': True, 'parallel_read_safe': False}
