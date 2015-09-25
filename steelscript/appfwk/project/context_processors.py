# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import django
from django.conf import settings

from steelscript.appfwk.apps.preferences.models import SystemSettings
from steelscript.appfwk.apps.plugins import plugins


def django_version(request):
    return {'django_version': django.VERSION}


def offline_js(request):
    return {'offline_js': settings.OFFLINE_JS}


def versions(request):
    return {'appfwk_version': settings.VERSION,
            'js_versions': settings.JS_VERSIONS}


def developer(request):
    return {'developer': SystemSettings.get_system_settings().developer}


def static_extensions(request):
    js = []
    css = []
    for plugin in plugins.all():
        if hasattr(plugin, 'js'):
            js.extend(plugin.js)
        if hasattr(plugin, 'css'):
            css.extend(plugin.css)

    return {'js_extensions': js,
            'css_extensions': css}
