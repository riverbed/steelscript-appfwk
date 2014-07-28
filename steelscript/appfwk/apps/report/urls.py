# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url
import steelscript.appfwk.apps.report.views as views

urlpatterns = patterns(
    'steelscript.appfwk.apps.report.views',
    url(r'^$', views.ReportView.as_view(),
        name='report-view-root'),

    url(r'^reload$', 'reload_config',
        name='reload-all'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/$',
        views.ReportView.as_view(),
        name='report-view'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/$',
        views.ReportView.as_view(),
        name='report-view'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/criteria/$',
        views.ReportCriteria.as_view(),
        name='report-criteria'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/tables/$',
        views.ReportTableList.as_view(),
        name='report-table-list'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/edit/$',
        views.ReportEditor.as_view(),
        name='report-editor'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/edit/diff/$',
        views.ReportEditorDiff.as_view(),
        name='report-editor-diff'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/edit/copy/$',
        views.ReportCopy.as_view(),
        name='report-editor-copy'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/reload$',
        'reload_config',
        name='reload-report'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/reload$',
        'reload_config',
        name='reload-report'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widgets$',
        views.ReportWidgets.as_view(),
        name='report-widgets'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_id>[0-9]+)/jobs/$',
        views.WidgetJobsList.as_view(),
        name='widget-job-list'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_id>[0-9]+)/criteria/$',
        views.ReportCriteria.as_view(),
        name='widget-criteria'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_id>[0-9]+)/jobs/(?P<job_id>[0-9]+)/$',
        views.WidgetJobDetail.as_view(),
        name='report-job-detail'),

    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/(?P<report_slug>[0-9_a-zA-Z]+)/widget/(?P<widget_slug>[0-9_a-zA-Z]+)/$',
        views.WidgetView.as_view(),
        name='widget-stand-alone'),

    # this makes more sense at the project level, but since its implemented
    # under `report`, lets have the url here for now
    url(r'^download_debug$', 'download_debug'),
)
