# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


"""
WSGI config for SteelScript App Framework

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

"""
import os
import sys

# Update this path as needed
PROJECT_ROOT = '/steelscript/steelscript_appfwk'

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "local_settings")
os.environ['HOME'] = PROJECT_ROOT
os.environ['DATAHOME'] = PROJECT_ROOT
sys.path.append(PROJECT_ROOT)

# borrow monkey patch from app framework manage.py module
from manage import find_management_module
import django.core.management
django.core.management.find_management_module = find_management_module


# Run the WSGI Server
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
