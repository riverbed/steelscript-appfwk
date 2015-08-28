# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url

from steelscript.appfwk.apps.jobs import views

urlpatterns = patterns(
    '',

    url(r'^$',
        views.JobList.as_view(),
        name='job-list'),

    url(r'^visualize/$',
        views.JobVisualize.as_view(),
        name='job-visualize'),

    url(r'^(?P<pk>[0-9]+)/$',
        views.JobDetail.as_view(),
        name='job-detail'),

    url(r'^(?P<pk>[0-9]+)/data/$',
        views.JobDetailData.as_view(),
        name='job-detail-data'),

    url(r'^(?P<pk>[0-9]+)/data/(?P<format>[a-z]+)/$',
        views.JobDetailData.as_view(),
        name='job-detail-data'),
)
