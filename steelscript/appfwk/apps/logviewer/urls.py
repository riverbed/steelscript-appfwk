# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url

import steelscript.appfwk.apps.logviewer.views as views


urlpatterns = patterns(
    'steelscript.appfwk.apps.logviewer.views',

    url(r'^$', views.LogViewer.as_view(), name='logviewer'),
)
