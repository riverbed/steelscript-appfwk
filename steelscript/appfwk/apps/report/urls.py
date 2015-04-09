# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url, include
import steelscript.appfwk.apps.report.views as views

PREFIX = 'steelscript.appfwk.apps.report.views'


def prefix_patterns(*args):
    return patterns(PREFIX,  *args)

# <name>_patterns below represents patterns of the url's suffix after <name>
# as /../../../<name>/<suffix>
# All report urls are built in reverse order (Otherwise it is not feasible
# as suffix patterns will need to be used before they even exists).
# Therefore, start from the bottom and work up to see how URLs are built.

job_patterns = prefix_patterns(
    url(r'^$', views.WidgetJobDetail.as_view(), name='report-job-detail'),
    url(r'^(?P<status>status)/$', views.WidgetJobDetail.as_view(),
        name='report-job-status'))

jobs_patterns = prefix_patterns(
    url(r'^$', views.WidgetJobsList.as_view(), name='widget-job-list'),
    url(r'^(?P<job_id>[0-9]+)/', include(job_patterns)))

widget_patterns = prefix_patterns(
    url(r'^$', views.WidgetDetailView.as_view(), name='widget-slug'),
    url(r'^render/$', views.WidgetView.as_view(), name='widget-stand-alone'),
    url(r'^authtoken/$', views.WidgetTokenView.as_view(),
        name='widget-auth-token'),
    url(r'^(?P<auth_token>[0-9_a-z]+)/editfields/$',
        views.EditFieldsView.as_view(), name='edit-fields'),
    url(r'^jobs/', include(jobs_patterns)),
    url(r'^criteria/$', views.ReportCriteria.as_view(),
        name='widget-criteria'))

widgets_patterns = prefix_patterns(
    url(r'^$', views.ReportWidgets.as_view(),
        name='report-widgets'),
    url(r'^(?P<widget_slug>[0-9_a-zA-Z-]+)/', include(widget_patterns)))

report_edit_patterns = prefix_patterns(
    url(r'^$', views.ReportEditor.as_view(), name='report-editor'),
    url(r'^diff/$', views.ReportEditorDiff.as_view(),
        name='report-editor-diff'),
    url(r'^copy/$', views.ReportCopy.as_view(), name='report-editor-copy'))

report_patterns = prefix_patterns(
    url(r'^$', views.ReportView.as_view(), name='report-view'),
    url(r'^print/$', views.ReportPrintView.as_view(),
        name='report-print-view'),
    url(r'^criteria/$', views.ReportCriteria.as_view(),
        name='report-criteria'),
    url(r'^tables/$', views.ReportTableList.as_view(),
        name='report-table-list'),
    url(r'^edit/', include(report_edit_patterns)),
    url(r'^reload/$', 'reload_config',  name='reload-report'),
    url(r'^widgets/', include(widgets_patterns)))

namespace_patterns = prefix_patterns(
    url(r'^$', views.ReportView.as_view(), name='report-view'),
    url(r'^(?P<report_slug>[0-9_a-zA-Z]+)/', include(report_patterns)),
    url(r'^reload/$', 'reload_config', name='reload-report'))

urlpatterns = prefix_patterns(
    url(r'^$', views.ReportView.as_view(), name='report-view-root'),
    url(r'^reload$', 'reload_config', name='reload-all'),
    url(r'^(?P<namespace>[0-9_a-zA-Z]+)/', include(namespace_patterns)),
    url(r'^download_debug$', 'download_debug'))
