# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    '',

    url(r'^ipaddr/(?P<addr>[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)$',
        'steelscript.appfwk.apps.geolocation.views.getIPAddress'),
    url(r'^location/(?P<name>.+)$',
        'steelscript.appfwk.apps.geolocation.views.getLocation')
    )
