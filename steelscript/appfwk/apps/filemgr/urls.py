# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from steelscript.appfwk.apps.filemgr.views import DataFileList, \
    DataFileDetail, DataFSSync, file_download


urlpatterns = patterns(
    '',

    url(r'^$',
        DataFileList.as_view(),
        name='datafile-list'),

    url(r'^(?P<datafile_id>[0-9]+)/$',
        DataFileDetail.as_view(),
        name='datafile-detail'),

    url(r'^add/$',
        DataFileDetail.as_view(),
        name='datafile-add'),

    url(r'^sync/$',
        DataFSSync.as_view(),
        name='datafilefs-sync'),

    url(r'^(?P<file_name>.*)/download/$',
        file_download,
        name='datafile-download'),

)

urlpatterns = format_suffix_patterns(urlpatterns)
