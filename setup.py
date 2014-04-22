#!/usr/bin/env python
"""
steelscript-appfw-core
======================

Core apps for Riverbed SteelScript Application Framework

"""
import os

try:
    from setuptools import setup, find_packages, Command
    packagedata = True
except ImportError:
    from distutils.core import setup
    from distutils.cmd import Command
    packagedata = False

    def find_packages(path='steelscript'):
        return [p for p, files, dirs in os.walk(path) if '__init__.py' in files]

from gitpy_versioning import get_version

setup_args = {
    'name':               'steelscript.appfw.core',
    'namespace_packages': ['steelscript'],
    'version':            get_version(),
    'author':             'Riverbed Technology',
    'author_email':       'eng-github@riverbed.com',
    'url':                'http://pythonhosted.org/steelscript',
    'description':        'Core apps for Riverbed SteelScript Application Framework',

    'long_description': """Core apps for SteelScript Application Framework
====================================================

SteelScript is a collection of libraries and scripts in Python and JavaScript for
interacting with Riverbed Technology devices.

For a complete guide to installation, see:

http://pythonhosted.org/steelscript/install.html
    """,
    'license': 'MIT',

    'platforms': 'Linux, Mac OS, Windows',

    'classifiers': (
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Networking',
        'Topic :: Software Development'
    ),

    'packages': find_packages(),

    'scripts': None,

    'install_requires': (
        'Django>=1.5.1,<1.6',
        'steelscript.common>=0.6',
        'steelscript.netprofiler>=0.1',
    ),

    'tests_require': (),

}

if packagedata:
    setup_args['include_package_data'] = True

setup(**setup_args)

