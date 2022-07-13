# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

import mock

MOCK_MODULES = ['functional_test_base', 'test_functional_other', 'test_hierarchical_code_lists', 
'test_history', 'test_inclusion_exclusion', 'test_regular_expressions', 'test_settings',  'test_search_filters',
'test_versioning', 'test_functional_read_only_conf_concept', 'clinicalcode.tests.functional_tests.read_only', 'read_only_test_settings',
]

DEBUG = False

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = mock.Mock()

from django.conf import settings
#settings.configure()
import django
sys.path.insert(0, os.path.abspath('../../../CodeListLibrary_project'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'cll.settings'
django.setup()

# -- Project information -----------------------------------------------------

project = 'Concept Library Coding Reference'
title = 'Title'
copyright = '2022, alex'
author = 'alex'

# The full version, including alpha/beta/rc tags
release = '1.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.todo', 'sphinx.ext.viewcode', 'sphinx.ext.autodoc', 'sphinxjp.themes.basicstrap']


# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['**/clinicalcode/migrations', 'clinicalcode/migrations', 'clinicalcode/migrations*', 'clinicalcode/migrations/*', 'migrations','_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'sphinx_rtd_theme'
html_title = 'Library Code Reference Data'
html__short_title = 'Library Code Reference Data'

html_theme = 'furo'
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_logo = "header_logo.png"
