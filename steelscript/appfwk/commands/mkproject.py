# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
from random import choice

from steelscript.common.utils import link_pkg_dir, link_pkg_files
from steelscript.commands.steel import (BaseCommand, prompt, console, debug,
                                        shell, check_git, ShellFailed)


LOCAL_CONTENT = """
from steelscript.appfwk.project.settings import *

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATAHOME = os.getenv('DATAHOME', PROJECT_ROOT)
DATA_CACHE = os.path.join(DATAHOME, 'data', 'datacache')
INITIAL_DATA = os.path.join(DATAHOME, 'data', 'initial_data')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
MEDIA_ROOT = DATA_CACHE

# Optionally add additional applications specific to this project instance

LOCAL_APPS = (
    # additional apps can be listed here
)
INSTALLED_APPS += LOCAL_APPS

# Configure database for development or production.

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',

        # Path to database file if using sqlite3.
        # Database name for others
        'NAME': os.path.join(DATAHOME, 'data', 'project.db'),

        'USER': '',     # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '',     # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',     # Set to empty string for default. Not used with sqlite3.
    }
}

# Setup loggers to local directory
LOGGING['handlers']['logfile']['filename'] = os.path.join(DATAHOME, 'logs', 'log.txt')
LOGGING['handlers']['backend-log']['filename'] = os.path.join(DATAHOME, 'logs', 'log-db.txt')

# To enable syslog handling instead of local logging, uncomment next block of LOGGING
# statements

# remove these loggers since the configuration will attempt to write the
# files even if they don't have a logger declared for them
#LOGGING['disable_existing_loggers'] = True
#LOGGING['handlers'].pop('logfile')
#LOGGING['handlers'].pop('backend-log')
#
#LOGGING['handlers']['syslog'] = {
#    'level': 'DEBUG',
#    'class': 'logging.handlers.SysLogHandler',
#    'formatter': 'standard_syslog',
#    'facility': SysLogHandler.LOG_USER,
#    'address': '/var/run/syslog' if sys.platform == 'darwin' else '/dev/log'
#}
#
#LOGGING['loggers'] = {
#    'django.db.backends': {
#        'handlers': ['null'],
#        'level': 'DEBUG',
#        'propagate': False,
#    },
#    '': {
#        'handlers': ['syslog'],
#        'level': 'INFO',
#        'propagate': True,
#    },
#}

"""

LOCAL_FOOTER = """
# Add other settings customizations below, which will be local to this
# machine only, and not recorded by git. This could include database or
# other authentications, LDAP settings, or any other overrides.

# For example LDAP configurations, see the file
# `project/ldap_example.py`.
"""

GITIGNORE = """
*~
*.pyc
*.swp
.DS_Store

data/
example-configs/
logs/
media
thirdparty
static/
"""


class Command(BaseCommand):
    help = 'Install new local App Framework project'

    def add_options(self, parser):
        parser.add_option('-d', '--dir', action='store',
                          help='Optional path for new project location')
        parser.add_option('-v', '--verbose', action='store_true',
                          help='Extra verbose output')
        parser.add_option('--no-git', action='store_true',
                          help='Do not initialize project as new git repo')
        parser.add_option('--no-init', action='store_true',
                          help='Do not initialize project with default '
                               'local settings')

    def debug(self, msg, newline=False):
        if self.options.verbose:
            debug(msg, newline=newline)

    def mkdir(self, dirname):
        """Creates directory if it doesn't already exist."""
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def create_local_settings(self, dirname):
        """Creates local settings configuration."""

        secret = ''.join([
            choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
            for i in range(50)
        ])

        fname = os.path.join(dirname, 'local_settings.py')
        if not os.path.exists(fname):
            console('Writing local settings %s ... ' % fname, newline=False)
            with open(fname, 'w') as f:
                f.write(LOCAL_CONTENT)
                f.write("SECRET_KEY = '%s'\n" % secret)
                f.write(LOCAL_FOOTER)
            console('done.')
        else:
            console('Skipping local settings generation.')

    def create_project_directory(self, dirpath):
        """Creates project directory and copies/links necessary files."""
        console('Creating project directory %s ...' % dirpath)
        self.mkdir(dirpath)

        # link manage.py and media directories
        # when symlink not available (windows) will copy files instead
        link_pkg_files('steelscript.appfwk.apps',
                       '../manage.py',
                       dirpath,
                       symlink=hasattr(os, 'symlink'),
                       buf=self.debug)

        for p in ('media', 'thirdparty'):
            link_pkg_dir('steelscript.appfwk.apps',
                         '../' + p,
                         os.path.join(dirpath, p),
                         symlink=hasattr(os, 'symlink'),
                         buf=self.debug)

        # copy and make folders
        self.mkdir(os.path.join(dirpath, 'logs'))

        datapath = os.path.join(dirpath, 'data')
        self.mkdir(datapath)
        link_pkg_dir('steelscript.appfwk.apps',
                     '../initial_data',
                     os.path.join(datapath, 'initial_data'),
                     symlink=False,
                     buf=self.debug)
        self.mkdir(os.path.join(datapath, 'datacache'))

        # copy example-configs
        link_pkg_files('steelscript.appfwk.apps',
                       '../project/example-configs/*',
                       os.path.join(dirpath, 'example-configs'),
                       symlink=False,
                       buf=self.debug)

        # copy sample locations
        link_pkg_files('steelscript.appfwk.apps',
                       'geolocation/sample_location*',
                       os.path.join(dirpath, 'example-configs'),
                       symlink=False,
                       buf=self.debug)

    def collectreports(self, dirpath):
        shell('python manage.py collectreports -v 3 --trace',
              msg='Collecting default reports',
              cwd=dirpath)

    def initialize_git(self, dirpath):
        """If git installed, initialize project folder as new repo.
        """
        try:
            check_git()
        except ShellFailed:
            return

        # we have git, lets make a repo
        shell('git init', msg='Initializing project as git repo',
              cwd=dirpath)
        fname = os.path.join(dirpath, '.gitignore')
        with open(fname, 'w') as f:
            f.write(GITIGNORE)
        shell('git add .',
              msg=None,
              cwd=dirpath)
        shell('git commit -a -m "Initial commit."',
              msg='Creating initial git commit',
              cwd=dirpath)

    def initialize_project(self, dirpath):
        shell('python manage.py initialize -v 3 --trace',
              msg='Initializing project with default settings',
              cwd=dirpath)

    def main(self):
        console('Generating new Application Framework project ...')

        dirpath = self.options.dir
        while not dirpath:
            default = os.path.join(os.getcwd(), 'appfwk_project')
            dirpath = prompt('\nEnter path for project files',
                             default=default)

        dirpath = os.path.abspath(dirpath)
        if os.path.exists(dirpath):
            console('Project directory already exists, aborting.')
            return

        self.create_project_directory(dirpath)
        self.create_local_settings(dirpath)
        self.collectreports(dirpath)
        if not self.options.no_git:
            self.initialize_git(dirpath)

        if not self.options.no_init:
            self.initialize_project(dirpath)

        console('\n*****\n')
        console('App Framework project created.')

        if self.options.no_init:
            console("Change to that directory and run "
                    "'steel appfwk init' to initialize the project.")
