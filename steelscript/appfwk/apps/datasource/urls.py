# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url

from steelscript.appfwk.apps.datasource import views

urlpatterns = patterns(
    '',

    url(r'^$',
        views.DatasourceRoot.as_view(),
        name='datasource-root'),

    url(r'^tables/$',
        views.TableList.as_view(),
        name='table-list'),

    url(r'^tables/(?P<pk>[0-9]+)/$',
        views.TableDetail.as_view(),
        name='table-detail'),

    url(r'^tables/(?P<pk>[0-9]+)/columns/$',
        views.TableColumnList.as_view(),
        name='table-column-list'),

    url(r'^tables/(?P<pk>[0-9]+)/jobs/$',
        views.TableJobList.as_view(),
        name='table-job-list'),

    url(r'^tables/fields/$',
        views.TableFieldList.as_view(),
        name='table-field-list'),

    url(r'^tables/fields/(?P<pk>[0-9]+)/$',
        views.TableFieldDetail.as_view(),
        name='table-field-detail'),

    url(r'^columns/$',
        views.ColumnList.as_view(),
        name='column-list'),

    url(r'^columns/(?P<pk>[0-9]+)/$',
        views.ColumnDetail.as_view(),
        name='column-detail'),
)
