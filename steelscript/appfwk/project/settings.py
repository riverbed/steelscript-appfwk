# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


# Django settings for SteelScript project project.
import os
import sys
import pkg_resources

# version information
VERSION = pkg_resources.get_distribution("steelscript.appfwk").version

DEBUG = True

SETTINGS_ROOT = os.path.abspath(__file__)
PORTAL_ROOT = os.path.dirname(SETTINGS_ROOT)
PROJECT_ROOT = os.path.dirname(PORTAL_ROOT)

# Development defaults
DATAHOME = os.getenv('DATAHOME', PROJECT_ROOT)
DATA_CACHE = os.path.join(DATAHOME, 'data', 'datacache')
INITIAL_DATA = os.path.join(DATAHOME, 'data', 'initial_data')
REPORTS_DIR = os.path.join(PROJECT_ROOT, 'reports')
LOG_DIR = os.path.join(DATAHOME, 'logs')

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

AUTH_USER_MODEL = 'preferences.AppfwkUser'
LOGIN_REDIRECT_URL = '/report'

DATABASES = {
    'default': {
        # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.sqlite3',

        # Path to database file if using sqlite3.
        # Database name for others
        'NAME': os.path.join(PROJECT_ROOT, 'project.db'),

        'USER': '',      # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',      # Set to empty string for default. Not used with sqlite3.
    }
}

# Task model, sync is the slowest but the only one guaranteed to
# work with sqlite3.  The other models require a database
# APPFWK_TASK_MODEL = 'sync'
APPFWK_TASK_MODEL = 'async'
# APPFWK_TASK_MODEL = 'celery'

# Location of progressd daemon, default for locally running
PROGRESSD_HOST = 'http://127.0.0.1'
PROGRESSD_PORT = '5000'
# Seconds that it takes to restart progressd with around 5000 jobs
PROGRESSD_CONN_TIMEOUT = 10

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Optional support for Guest users
GUEST_USER_ENABLED = False
GUEST_USER_NAME = 'Guest'             # display name when in guest-mode
GUEST_USER_TIME_ZONE = 'US/Eastern'   # timezone to use when in guest-mode
GUEST_SHOW_BUTTON = True              # whether to show user button when Guest

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'datacache')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# If you set this to True, templates will look for local copies of the JS libs
# that we normally get off the cloud.
OFFLINE_JS = False

JS_VERSIONS = {
    'bootstrap': '3.3.7',
    'jquery': '1.12.4',
    'jqueryui': '1.10.2',
    'jqueryform': '3.32',
    'yui': '3.17.2',
    'c3': '0.4.11',
    'd3': '3.5.17',
    'pivottable': '2.1.0',
    'datatables': '1.10.12',
}

# Format: (url, dirname). If dirname is None, "steel appfwk mkproject" will
# install the file directly into the offline JS dir. Otherwise, it will treat
# the file as a zip or tar archive and extract it into that subdirectory.

# JS_FILES are files that would be used in both online/offline scenarios.
JS_FILES = [
    ("https://cdnjs.cloudflare.com/ajax/libs/jquery/{0}/jquery.min.js"
     .format(JS_VERSIONS['jquery']), None),
    ("https://cdnjs.cloudflare.com/ajax/libs/jquery.form/{0}/jquery.form.js"
     .format(JS_VERSIONS['jqueryform']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/c3/{0}/c3.min.js'
     .format(JS_VERSIONS['c3']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/d3/{0}/d3.min.js'
     .format(JS_VERSIONS['d3']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/pivottable/{0}/pivot.min.js'
     .format(JS_VERSIONS['pivottable']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/datatables/{0}/js/jquery.dataTables.min.js'
     .format(JS_VERSIONS['datatables']), None),
]

ONLINE_JS_FILES = JS_FILES + [
    ("https://cdnjs.cloudflare.com/ajax/libs/jqueryui/{0}/jquery-ui.min.js"
        .format(JS_VERSIONS['jqueryui']), None),
    ("https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/{0}/js/bootstrap.min.js"
        .format(JS_VERSIONS['bootstrap']), None),
]

OFFLINE_JS_FILES = [
    ("https://github.com/twbs/bootstrap/releases/download/v{ver}/bootstrap-{ver}-dist.zip"
        .format(ver=JS_VERSIONS['bootstrap']),
     "bootstrap-{ver}".format(ver=JS_VERSIONS['bootstrap'])),
    ("https://jqueryui.com/resources/download/jquery-ui-{0}.zip"
        .format(JS_VERSIONS['jqueryui']), "jquery-ui"),
    ("http://yui.zenfs.com/releases/yui3/yui_{0}.zip"
        .format(JS_VERSIONS['yui']), "yui"),
]

OFFLINE_JS_FILES.extend(JS_FILES)

# CSS_FILES are files that would be used in both online/offline scenarios.
CSS_FILES = [
    ('https://cdnjs.cloudflare.com/ajax/libs/c3/{0}/c3.min.css'
     .format(JS_VERSIONS['c3']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/pivottable/{0}/pivot.min.css'
     .format(JS_VERSIONS['pivottable']), None),
    ('https://cdnjs.cloudflare.com/ajax/libs/datatables/{0}/css/jquery.dataTables.min.css'
     .format(JS_VERSIONS['datatables']), None),
]

ONLINE_CSS_FILES = [
    ("https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/{0}/css/bootstrap.min.css"
        .format(JS_VERSIONS['bootstrap']), None),
    ("https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/{0}/css/bootstrap-theme.min.css"
        .format(JS_VERSIONS['bootstrap']), None),
] + CSS_FILES

OFFLINE_CSS_FILES = CSS_FILES

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, 'media'),
    os.path.join(PROJECT_ROOT, 'thirdparty'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'yc6!d7figlp%$$mhjio-9hn$zr9ot+zp)y8)un)rt^rukcwm^t'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(PROJECT_ROOT, 'templates'),
        ],
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.core.context_processors.request',
                'django.contrib.messages.context_processors.messages',
                'steelscript.appfwk.project.context_processors.appfwk_vars',
                'steelscript.appfwk.project.context_processors.static_extensions',
                'steelscript.appfwk.apps.report.context_processors.report_list_processor',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
                'django.template.loaders.eggs.Loader',
                'admin_tools.template_loaders.Loader',
            ]
        },
    },
]

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'steelscript.appfwk.apps.report.middleware.exceptions.ReloadExceptionHandler',
    'steelscript.appfwk.apps.report.middleware.timezones.TimezoneMiddleware',
    #'project.middleware.LoginRequiredMiddleware',

    # hitcount
    'steelscript.appfwk.apps.hitcount.middleware.CounterMiddleware',
)

ROOT_URLCONF = 'steelscript.appfwk.project.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'steelscript.appfwk.project.wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'admin_tools',
    'admin_tools.theming',
    'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.admin',
    'tagging',
    'tagging_autocomplete',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',

    # third-party apps
    'rest_framework',
    'django_extensions',
    'django_ace',
    'pinax.announcements',

    # appfwk apps - order matters, django loads in sequence
    'steelscript.appfwk.apps.datasource',
    'steelscript.appfwk.apps.devices',
    'steelscript.appfwk.apps.pcapmgr',
    'steelscript.appfwk.apps.report',
    'steelscript.appfwk.apps.geolocation',
    'steelscript.appfwk.apps.help',
    'steelscript.appfwk.apps.preferences',
    'steelscript.appfwk.apps.plugins',
    'steelscript.appfwk.apps.alerting',
    'steelscript.appfwk.apps.jobs',
    'steelscript.appfwk.apps.logviewer',
    'steelscript.appfwk.apps.metrics',
    'steelscript.appfwk.apps.hitcount',
    'steelscript.appfwk.apps.db',

    # 'standard' plugins
    'steelscript.appfwk.apps.plugins.builtin.whois',
    'steelscript.appfwk.apps.plugins.builtin.solarwinds',
    'steelscript.appfwk.apps.plugins.builtin.sharepoint',
    'steelscript.appfwk.apps.plugins.builtin.metrics_plugin',
)

ADMIN_TOOLS_MENU = 'steelscript.appfwk.project.menu.CustomMenu'
ADMIN_TOOLS_THEMING_CSS = 'css/theming.css'
ADMIN_TOOLS_INDEX_DASHBOARD = 'steelscript.appfwk.project.dashboard.CustomIndexDashboard'
ADMIN_TOOLS_APP_INDEX_DASHBOARD = 'steelscript.appfwk.project.dashboard.CustomAppIndexDashboard'

from steelscript.appfwk.apps.plugins.loader import load_plugins
load_plugins()

REST_FRAMEWORK = {
    # Use hyperlinked styles by default.
    # Only used if the `serializer_class` attribute is not set on a view.
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',

    # Use Django's standard `django.contrib.auth` permissions,
    'DEFAULT_PERMISSION_CLASSES': [
        # default, no guest access:
        'rest_framework.permissions.IsAuthenticated'
        # with guest access enabled:
        # 'rest_framework.permissions.AllowAny'
    ],

    'EXCEPTION_HANDLER':
        'steelscript.appfwk.project.middleware.authentication_exception_handler'
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
from logging.handlers import SysLogHandler

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)-5s] %(process)d/%(thread)d %(name)s:%(lineno)s - %(message)s'
        },
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'standard_syslog': {
            #'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            'format': '%(asctime)s SteelScript AppFramework: [%(levelname)-5s] %(name)s:%(lineno)s - %(message)s',
            'datefmt': '%b %d %H:%M:%S',
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'steelscript.appfwk.project.nullhandler.NullHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 5,            # 5 MB
            'backupCount': 1,
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIR, 'log.txt')
        },
        'backend-log': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 5,            # 5 MB
            'backupCount': 1,
            'formatter': 'verbose',
            'filename': os.path.join(LOG_DIR, 'log-db.txt')
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['backend-log'],
            'level': 'DEBUG',
            'propagate': False,
        },
        '': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
    }
}

# Configure log viewer app options
LOGVIEWER_ENABLE_SYSLOGS = True
LOGVIEWER_SYSLOGS_DIR = '/var/log'
LOGVIEWER_SYSLOGS_PATTERNS = (r'messages(-)?([0-9]+)?', r'cron(-)?([0-9]+)?',
                              r'dmesg', r'boot.log', r'appfwk', 'progressd.*')

LOGVIEWER_CELERY_SYSLOGS_DIR = '/var/log/celery'
LOGVIEWER_CELERY_SYSLOGS_PATTERNS = (r'.*.log',)

LOGVIEWER_ENABLE_HTTPD_LOGS = True
LOGVIEWER_HTTPD_DIR = os.path.join(LOGVIEWER_SYSLOGS_DIR, 'httpd')  # debian
LOGVIEWER_HTTPD_PATTERNS = (r'(ssl_)?access_log(-)?([0-9]+)?',
                            r'(ssl_)?error_log(-)?([0-9]+)?')

# default logs
LOGVIEWER_LOG_PATTERNS = (r'log(-db)?.txt(.[1-9])?',
                          r'celery.txt(.[1-9])?')

GLOBAL_ERROR_HANDLERS = (
    {'sender': 'LoggingSender',
     'template': 'Error processing job: {message}'},
)

#
# App Framework custom settings
#

# Strip device passwords from fixture that gets written to disk.  Should remain
# True in all production settings.  If False, the passwords will be stored to
# disk to aid in development workflows.
APPFWK_STRIP_DEVICE_PASSWORDS = True

# Job aging parameters
# Used as a form of datasource caching, jobs older than the 'ancient'
# threshold will be deleted regardless, while 'old' jobs will
# only be deleted if no other jobs are referencing their data.
APPS_DATASOURCE = {
    'job_age_old_seconds': 60*60*24,            # one day
    'job_age_ancient_seconds': 7*60*60*24,      # one week
    'threading': True
}

TESTING = 'test' in sys.argv
TEST_RUNNER = 'steelscript.appfwk.project.testing.AppfwkTestRunner'

if TESTING:
    PROGRESSD_PORT = '5555'

LOCAL_APPS = None

# List of modules that should be available for synthetic
# column computations.  These are imported into by
# datasource.models at run time
APPFWK_SYNTHETIC_MODULES = (
    'pandas',
    )

# Size limit of all netshark downloaded pcap files in bytes (default 10GB)
PCAP_SIZE_LIMIT = 10000000000

# Create report history
REPORT_HISTORY_ENABLED = True

# Hitcount parameters
#  Visted URLs in the following list (based on regular expression
#  search, see https://docs.python.org/2/library/re.html) will be ignored, and
#  will not be displayed on admin page.
HITCOUNT_IGNORE_URLS = [
    '/admin/', '/accounts/', '/favicon.ico', r'/report/.*/jobs/[0-9]+/'
]

# DB solution
DB_SOLUTION = 'elastic'
ELASTICSEARCH_HOSTS = ['elasticsearch']
