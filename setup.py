# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os

try:
    from setuptools import setup, find_packages, Command
    packagedata = True
except ImportError:
    from distutils.core import setup
    from distutils.cmd import Command
    packagedata = False

    def find_packages(where='steelscript', exclude=None):
        return [p for p, files, dirs in os.walk(where) if '__init__.py' in files]

from gitpy_versioning import get_version

setup_args = {
    'name':               'steelscript.appfwk',
    'namespace_packages': ['steelscript'],
    'version':            get_version(),
    'author':             'Riverbed Technology',
    'author_email':       'eng-github@riverbed.com',
    'url':                'http://pythonhosted.org/steelscript',
    'license':            'MIT',
    'description':        'Core apps for Riverbed SteelScript Application Framework',

    'long_description': """Core apps for SteelScript Application Framework
====================================================

The SteelScript Application Framework makes it easy to create a fully
custom web application that mashes up data from multiple sources.  It comes
pre-configured with several reports for NetProfiler and NetShark.

For a complete guide to installation, see:

http://pythonhosted.org/steelscript/
    """,

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

    'packages': find_packages(exclude=('gitpy_versioning','data')),

    'entry_points': {
        'steel.commands': [
            'appfwk = steelscript.appfwk.commands'
        ],
    },

    'scripts': None,

    'install_requires': (
        'Django>=1.5.1,<1.6',
        'steelscript>=0.6',
        'steelscript.netprofiler>=0.1',

        'djangorestframework==2.3.13',
        'django-extensions==1.3.7',
        'django-model-utils==2.0.3',
        'jsonfield==0.9.20',
        'numpy>=1.8.0,<1.9',
        'pandas==0.13.1',
        'pygeoip>=0.2.6',
        'python-dateutil>=2.2',
        'pytz>=2013.8',
        'six>=1.3.0',
        'wsgiref>=0.1.2',
        'django-announcements==1.2.0',

        'django-admin-tools==0.5.1',

        'ansi2html>=1.0.6',
        'django-ace==1.0.1',
    ),

    'tests_require': (),

}

data_files = []

for path, subdirs, files in os.walk('steelscript/appfwk/commands/data'):
    for n in files:
        if n.endswith('~') or n.endswith('.pyc') or n.endswith('#'):
            continue

        data_files.append(
            os.path.join(path.replace('steelscript/appfwk/commands/', ''), n))

setup_args['package_data'] = {'steelscript.appfwk.commands' : data_files}

if packagedata:
    setup_args['include_package_data'] = True

setup(**setup_args)
