# Copyright 2012-present MongoDB, Inc.
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

import re

from docutils.nodes import doctest_block, literal_block
from sphinx import addnodes
from sphinx.addnodes import desc, desc_content, desc_signature, seealso, versionmodified
from sphinx.util.inspect import safe_getattr

import motor
import motor.core

# This is a place to store info while parsing, to be used before generating.
motor_info = {}


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


docstring_warnings = []


def maybe_warn_about_code_block(name, content_node):
    if has_node_of_type(content_node, (literal_block, doctest_block)):
        docstring_warnings.append(name)


def has_coro_annotation(signature_node):
    try:
        return "coroutine" in signature_node[0][0]
    except IndexError:
        return False


def process_motor_nodes(app, doctree):
    # Search doctree for Motor's methods and attributes whose docstrings were
    # copied from PyMongo, and fix them up for Motor:
    #   1. Add a 'coroutine' annotation to the beginning of the declaration.
    #   2. Remove all version annotations like "New in version 2.0" since
    #      PyMongo's version numbers are meaningless in Motor's docs.
    #   3. Remove "seealso" directives that reference PyMongo's docs.
    #
    # We do this here, rather than by registering a callback to Sphinx's
    # 'autodoc-process-signature' event, because it's way easier to handle the
    # parsed doctree before it's turned into HTML than it is to update the RST.
    for objnode in doctree.traverse(desc):
        if objnode["objtype"] in ("method", "attribute"):
            signature_node = find_by_path(objnode, [desc_signature])[0]
            name = ".".join([signature_node["module"], signature_node["fullname"]])

            assert name.startswith("motor.")
            obj_motor_info = motor_info.get(name)
            if obj_motor_info:
                desc_content_node = find_by_path(objnode, [desc_content])[0]
                if desc_content_node.line is None and obj_motor_info["is_pymongo_docstring"]:
                    maybe_warn_about_code_block(name, desc_content_node)

                if obj_motor_info["is_async_method"]:
                    # Might be a handwritten RST with "coroutine" already.
                    if not has_coro_annotation(signature_node):
                        coro_annotation = addnodes.desc_annotation(
                            "coroutine ", "coroutine ", classes=["coro-annotation"]
                        )

                        signature_node.insert(0, coro_annotation)

                if obj_motor_info["is_pymongo_docstring"]:
                    # Remove all "versionadded", "versionchanged" and
                    # "deprecated" directives from the docs we imported from
                    # PyMongo
                    version_nodes = find_by_path(desc_content_node, [versionmodified])

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
    attr = safe_getattr(motor_class, name, *defargs)

    # Store some info for process_motor_nodes()
    full_name = "%s.%s.%s" % (motor_class.__module__, motor_class.__name__, name)

    full_name_legacy = "motor.%s.%s.%s" % (motor_class.__module__, motor_class.__name__, name)

    # These sub-attributes are set in motor.asynchronize()
    has_coroutine_annotation = getattr(attr, "coroutine_annotation", False)
    is_async_method = getattr(attr, "is_async_method", False)
    is_cursor_method = getattr(attr, "is_motorcursor_chaining_method", False)
    if is_async_method or is_cursor_method:
        pymongo_method = getattr(motor_class.__delegate_class__, attr.pymongo_method_name)
    else:
        pymongo_method = None

    # attr.doc is set by statement like 'error = AsyncRead(doc="OBSOLETE")'.
    is_pymongo_doc = pymongo_method and attr.__doc__ == pymongo_method.__doc__

    motor_info[full_name] = motor_info[full_name_legacy] = {
        "is_async_method": is_async_method or has_coroutine_annotation,
        "is_pymongo_docstring": is_pymongo_doc,
        "pymongo_method": pymongo_method,
    }

    return attr


pymongo_ref_pat = re.compile(r":doc:`(.*?)`", re.MULTILINE)


def _sub_pymongo_ref(match):
    ref = match.group(1)
    return ":doc:`%s`" % ref.lstrip("/")


def process_motor_docstring(app, what, name, obj, options, lines):
    if name in motor_info and motor_info[name].get("is_pymongo_docstring"):
        joined = "\n".join(lines)
        subbed = pymongo_ref_pat.sub(_sub_pymongo_ref, joined)
        lines[:] = subbed.split("\n")


def build_finished(app, exception):
    if not exception and docstring_warnings:
        print("PyMongo docstrings with code blocks that need update:")
        for name in sorted(docstring_warnings):
            print(name)


def setup(app):
    app.add_autodoc_attrgetter(type(motor.core.AgnosticBase), get_motor_attr)
    app.connect("autodoc-process-docstring", process_motor_docstring)
    app.connect("doctree-read", process_motor_nodes)
    app.connect("build-finished", build_finished)
    return {"parallel_write_safe": True, "parallel_read_safe": False}
