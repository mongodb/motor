# -*- coding: utf-8 -*-
#
# Motor documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing dir.

import sys, os
sys.path[0:0] = [os.path.abspath('..')]

from pymongo import version as pymongo_version
import motor

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.doctest', 'sphinx.ext.coverage',
              'sphinx.ext.todo', 'doc.mongo_extensions', 'doc.motor_extensions',
              'sphinx.ext.intersphinx', 'doc.coroutine_annotation']

primary_domain = 'py'

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Motor'
copyright = u'2016-present MongoDB, Inc.'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = motor.version
# The full version, including alpha/beta/rc tags.
release = motor.version

# List of documents that shouldn't be included in the build.
unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# -- Options for extensions ----------------------------------------------------
autoclass_content = 'init'

doctest_path = [os.path.abspath('..')]

# Don't test examples pulled from PyMongo's docstrings just because they start
# with '>>>'
doctest_test_doctest_blocks = ''

doctest_global_setup = """
import pprint
import sys
from datetime import timedelta

from tornado import gen
from tornado.ioloop import IOLoop

import pymongo
from pymongo.mongo_client import MongoClient

sync_client = MongoClient()
ismaster = sync_client.admin.command('isMaster')
server_info = sync_client.server_info()

if 'setName' in ismaster:
    raise Exception(
        "Run doctests with standalone MongoDB 4.0 server, not a replica set")

if ismaster.get('msg') == 'isdbgrid':
    raise Exception(
        "Run doctests with standalone MongoDB 4.0 server, not mongos")

if server_info['versionArray'][:2] != [4, 0]:
    raise Exception(
        "Run doctests with standalone MongoDB 4.0 server, not %s" % (
            server_info['version'], ))

sync_client.drop_database("doctest_test")
db = sync_client.doctest_test

import motor
from motor import MotorClient
"""

# -- Options for HTML output ---------------------------------------------------

html_copy_source = False

# Theme gratefully vendored from CPython source.
html_theme = "pydoctheme"
html_theme_path = ["."]
html_theme_options = {'collapsiblesidebar': True}
html_static_path = ['static']

html_sidebars = {
   'index': ['globaltoc.html', 'searchbox.html'],
}

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
# Note: html_js_files was added in Sphinx 1.8.
html_js_files = [
    'delighted.js',
]

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'Motor' + release.replace('.', '_')


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Motor.tex', u'Motor Documentation',
   u'A. Jesse Jiryu Davis', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

autodoc_default_flags = ['inherited-members']
autodoc_member_order = 'groupwise'

pymongo_inventory = ('https://pymongo.readthedocs.io/en/%s/' % pymongo_version,
                     None)

intersphinx_mapping = {
    'bson': pymongo_inventory,
    'gridfs': pymongo_inventory,
    'pymongo': pymongo_inventory,
    'aiohttp': ('http://aiohttp.readthedocs.io/en/stable/', None),
    'tornado': ('http://www.tornadoweb.org/en/stable/', None),
    'python': ('https://docs.python.org/3/', None),
}
