# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import re
import requests
import tempfile

from random import choice

from steelscript.common.pkgutils import link_pkg_dir, link_pkg_files
from steelscript.commands.steel import (BaseCommand, prompt, console, debug,
                                        shell, check_git, ShellFailed)

from steelscript.appfwk.project import settings

LOCAL_CONTENT = """
from steelscript.appfwk.project.settings import *

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATAHOME = os.getenv('DATAHOME', PROJECT_ROOT)
PCAP_STORE = os.path.join(DATAHOME, 'data', 'pcap')
DATA_CACHE = os.path.join(DATAHOME, 'data', 'datacache')
INITIAL_DATA = os.path.join(DATAHOME, 'data', 'initial_data')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')
LOG_DIR = os.path.join(DATAHOME, 'logs')

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
MEDIA_ROOT = DATA_CACHE

# Task model specific configs
APPFWK_TASK_MODEL = 'async'
#APPFWK_TASK_MODEL = 'celery'

if APPFWK_TASK_MODEL == 'celery':
    LOCAL_APPS = (
        'djcelery',
    )
    INSTALLED_APPS += LOCAL_APPS

    # redis for broker and backend
    BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_ACKS_LATE = True

    import djcelery
    djcelery.setup_loader()

    #CELERY_ALWAYS_EAGER = True
    TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

# Optionally add additional applications specific to this project instance
LOCAL_APPS = (
    # additional apps can be listed here
)
INSTALLED_APPS += LOCAL_APPS

# Optionally enable Guest read-only access to reports
GUEST_USER_ENABLED = False
GUEST_USER_TIME_ZONE = 'US/Eastern'

if GUEST_USER_ENABLED:
    # adjust authentication parameters
    REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = ['rest_framework.permissions.AllowAny']
    REST_FRAMEWORK.pop('EXCEPTION_HANDLER')

# Configure database for development or production.

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',

        # Path to database file if using sqlite3.
        # Database name for others
        'NAME': os.path.join(DATAHOME, 'data', 'project.db'),

        # USER, PASSWORD, HOST and PORT are not used by sqlite3.
        'USER': '',
        'PASSWORD': '',
        'HOST': '',  # Set to empty string for localhost.
        'PORT': '',  # Set to empty string for default.
    }
}

# Setup loggers to local directory
LOGGING['handlers']['logfile']['filename'] = os.path.join(LOG_DIR, 'log.txt')
LOGGING['handlers']['backend-log']['filename'] = os.path.join(LOG_DIR,
                                                              'log-db.txt')

# Optionally add additional global error handlers

LOCAL_ERROR_HANDLERS = (
    # additional global error handlers can be listed here
)
GLOBAL_ERROR_HANDLERS += LOCAL_ERROR_HANDLERS

# Overwrite overall size limit of all Netshark Pcap downloaded files in Bytes
# PCAP_SIZE_LIMIT = 10000000000

# To enable syslog handling instead of local logging, see the next blocks of
# LOGGING statements.  Note the different section for Linux/Mac vs Windows.

# remove these loggers since the configuration will attempt to write the
# files even if they don't have a logger declared for them
#LOGGING['disable_existing_loggers'] = True
#LOGGING['handlers'].pop('logfile')
#LOGGING['handlers'].pop('backend-log')
#
# Use the following handler for Linux/BSD/Mac machines
#LOGGING['handlers']['syslog'] = {
#    'level': 'DEBUG',
#    'class': 'logging.handlers.SysLogHandler',
#    'formatter': 'standard_syslog',
#    'facility': SysLogHandler.LOG_USER,
#    'address': '/var/run/syslog' if sys.platform == 'darwin' else '/dev/log'
#}
#
# Use the following handler for sending to Windows Event logs,
# you will need an additional package for Windows: Python for Windows
# Extensions, which can be found here:
#    http://sourceforge.net/projects/pywin32/files/pywin32/
#LOGGING['handlers']['syslog'] = {
#    'level': 'DEBUG',
#    'class': 'logging.handlers.NTEventLogHandler',
#    'formatter': 'standard_syslog',
#    'appname': 'steelscript',
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
        parser.add_option(
            '--offline-js', action='store_true',
            help=('Download local copies of cloud JavaScript libraries to '
                  'allow for offline use. (Google Maps and OpenStreetMaps are '
                  'not available offline.)')
        )

    def debug(self, msg, newline=False):
        if self.options.verbose:
            debug(msg, newline=newline)

    def mkdir(self, dirname):
        """Creates directory if it doesn't already exist."""
        if not os.path.exists(dirname):
            os.mkdir(dirname)

    def create_local_settings(self, dirname):
        """Creates local settings configuration."""

        secret = ''.join(
            choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
            for i in range(50)
        )

        fname = os.path.join(dirname, 'local_settings.py')
        if not os.path.exists(fname):
            console('Writing local settings %s ... ' % fname, newline=False)
            with open(fname, 'w') as f:
                f.write(LOCAL_CONTENT)
                if self.options.offline_js:
                    f.write("OFFLINE_JS = True\n")
                    f.write("STATICFILES_DIRS += (os.path.join(PROJECT_ROOT, "
                            "'offline'), )\n")
                else:
                    f.write("#OFFLINE_JS = True\n")
                    f.write("#STATICFILES_DIRS += (os.path.join(PROJECT_ROOT, "
                            "'offline'), )\n")
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

    def get_offline_js(self, dirpath):
        console("Downloading offline JavaScript files...")

        offline_js_dir = os.path.join(dirpath, 'offline')
        self.mkdir(offline_js_dir)

        failedurls = set()
        offline_files = settings.OFFLINE_JS_FILES + settings.OFFLINE_CSS_FILES
        for url, dirname in offline_files:
            filename = url.rsplit('/', 1)[1]

            console("Downloading {0}... ".format(url), newline=False)

            connectionfailed = False
            try:
                r = requests.get(url, stream=True, allow_redirects=True)
            except requests.exceptions.Timeout:
                console("failed: request timed out.".format(filename))
                connectionfailed = True
            except requests.exceptions.ConnectionError as e:
                console("failed with connection error: {0}".format(e))
                connectionfailed = True

            if connectionfailed:
                failedurls.add(url)
            elif r.status_code != requests.codes.ok:
                console("failed with HTTP status code {0}.".format(filename,
                        r.status_code))
                failedurls.add(url)
            else:
                if dirname is not None:
                    f = tempfile.NamedTemporaryFile(delete=False)
                    downloadpath = f.name
                else:
                    downloadpath = os.path.join(offline_js_dir, filename)
                    f = open(downloadpath, 'w')

                for chunk in r:
                    f.write(chunk)
                f.close()

                console("success.")

                # If dirname is not None, that means the file is a zip or tar
                # archive and should be extracted to that subdirectory.
                if dirname is not None:
                    finaldir = os.path.join(offline_js_dir, dirname)
                    console("Extracting to " + finaldir + "... ",
                            newline=False)
                    os.mkdir(finaldir)
                    try:
                        # when original url gets redirected to the cloud,
                        # the zip file would be moved to the middle
                        # hence search for string of '.zip' followed by
                        # Non-alphanumeric letters

                        if r.url.endswith('zip') or \
                                re.search('.zip[^a-zA-Z\d]', r.url):
                            # Unzip into temporary dir, then move the contents
                            # of the outermost dir where we want. (With tar we
                            # can just use --strip-components 1.)
                            unzipdir = tempfile.mkdtemp()
                            shell("unzip {0} -d {1}".format(downloadpath,
                                                            unzipdir))
                            shell("mv -v {0}/*/* {1}".format(unzipdir,
                                                             finaldir))
                            shell("rm -rf {0}".format(unzipdir))
                        else:  # Not a zip, assume tarball.
                            self.mkdir(finaldir)
                            shell(("tar xvf {0} --strip-components 1 "
                                  "--directory {1}").format(downloadpath,
                                                            finaldir))
                    except Exception as e:
                        # This will probably be a ShellFailed exception, but
                        # we need to clean up the file no matter what.
                        raise e
                    finally:
                        os.remove(downloadpath)

                    console("success.")

        if failedurls:
            console("Warning: the following offline JavaScript files failed "
                    "to download. To complete this installation, you must "
                    "manually download these files to " + offline_js_dir + ".")

            for url, dirname in settings.OFFLINE_JS_FILES:
                if url in failedurls:
                    console("    {0}".format(url))
                    if dirname is not None:
                        console("   (this file is an archive -- extract to %s)"
                                % os.path.join(offline_js_dir, dirname))
        else:
            console("Done.")

    def initialize_git(self, dirpath):
        """Initialize project folder as new repo, if git installed."""
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

        if self.options.offline_js:
            self.get_offline_js(dirpath)

        if not self.options.no_git:
            self.initialize_git(dirpath)

        if not self.options.no_init:
            self.initialize_project(dirpath)

        console('\n*****\n')
        console('App Framework project created.')

        if self.options.no_init:
            console("Change to that directory and run "
                    "'steel appfwk init' to initialize the project.")
