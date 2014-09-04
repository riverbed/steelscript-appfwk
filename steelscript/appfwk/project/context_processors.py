# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import django
from django.conf import settings
import steelscript.appfwk.project.settings

def django_version(request):
    return { 'django_version': django.VERSION }

def offline_js(request):
    return { 'offline_js': settings.OFFLINE_JS }

def js_versions(request):
	return { 'js_versions': settings.JS_VERSIONS }