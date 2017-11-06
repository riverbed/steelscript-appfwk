# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url

import steelscript.appfwk.apps.help.views as views


urlpatterns = patterns(
    'steelscript.appfwk.apps.help.views',

    url(r'^about/$',
        views.SteelAbout.as_view()),

    url(r'^(?P<device_type>[a-z]+)/$',
        views.ColumnHelper.as_view()),

    # appresponse/columns or appresponse/sources
    url(r'appresponse/(?P<data_type>[a-z]+)/$',
        views.AppResponseHelper.as_view()),
)
