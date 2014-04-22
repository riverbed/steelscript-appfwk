# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.


from django.conf.urls import patterns, url
import steelscript.appfw.core.apps.preferences.views as views

urlpatterns = patterns(
    'steelscript.appfw.core.apps.report.views',
    url(r'^user/$', views.PreferencesView.as_view(), name='preferences'),
    url(r'^system/$', views.SystemSettingsView.as_view(), name='system_settings'),
)
