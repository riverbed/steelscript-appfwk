# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import django
from django.conf import settings

from steelscript.appfwk.apps.preferences.models import SystemSettings
from steelscript.appfwk.apps.plugins import plugins


def appfwk_vars(request):
    return {
        'django_version': django.VERSION,
        'offline_js': settings.OFFLINE_JS,
        'appfwk_version': settings.VERSION,
        'js_versions': settings.JS_VERSIONS,
        'js_files': settings.ONLINE_JS_FILES,
        'css_files': settings.ONLINE_CSS_FILES,
        'developer': SystemSettings.get_system_settings().developer,
        'guest_enabled': settings.GUEST_USER_ENABLED,
        'guest_show_button': settings.GUEST_SHOW_BUTTON,
        'report_history_enabled': settings.REPORT_HISTORY_ENABLED,
    }


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
