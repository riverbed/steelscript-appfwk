# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.conf.urls import patterns, url

from steelscript.appfwk.apps.alerting import views

urlpatterns = patterns(
    '',

    url(r'^$',
        views.AlertingRoot.as_view(),
        name='alerting-root'),

    url(r'^alerts/$',
        views.AlertList.as_view(),
        name='alert-list'),

    url(r'^alerts/(?P<pk>[0-9]+)/$',
        views.AlertDetail.as_view(),
        name='alert-detail'),

    url(r'^events/$',
        views.EventList.as_view(),
        name='event-list'),

    url(r'^events/(?P<pk>[0-9]+)/$',
        views.EventDetail.as_view(),
        name='event-detail'),

    # event detail by eventid instead
    url(r'^events/(?P<eventid>[a-z0-9-]+)/$',
        views.EventLookup.as_view(),
        name='event-lookup'),
)
