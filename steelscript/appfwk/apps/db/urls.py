# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.conf.urls import patterns, url

import steelscript.appfwk.apps.db.views as views


urlpatterns = patterns(
    'steelscript.appfwk.apps.db.views',

    url(r'^records/$',
        views.Records.as_view()),

    url(r'^handles/$',
        views.Handles.as_view()),
)
