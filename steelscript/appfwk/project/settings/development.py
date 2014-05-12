
from project.settings.base import *

# This file adds site specific options to the server settings
# To activate this file for use, include the following option as part of
# "manage.py" commands:
#   --settings=project.settings_local
#
# For example:
#   $ ./clean --reset --force --settings=project.settings_local

# Optionally add additional applications specific to this webserver

LOCAL_APPS = (
    # additional apps can be listed here
)
INSTALLED_APPS += LOCAL_APPS

# Configure alternate databases for development or production.  Leaving this
# section commented will default to the development sqlite database.

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',      # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
#        'NAME': os.path.join(PROJECT_ROOT, 'project.db'),  # Or path to database file if using sqlite3.
#        #'TEST_NAME': os.path.join(PROJECT_ROOT, 'test_project.db'),  # Or path to database file if using sqlite3.
#        'USER': '',                      # Not used with sqlite3.
#        'PASSWORD': '',                  # Not used with sqlite3.
#        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
#        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
#    }
#}

# Add other settings customizations below, which will be local to this
# machine only, and not recorded by git. This could include database or
# other authentications, LDAP settings, or any other overrides.

# For example LDAP configurations, see the file
# `project/ldap_example.py`.
