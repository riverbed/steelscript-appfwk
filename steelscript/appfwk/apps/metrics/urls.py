# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from steelscript.appfwk.apps.metrics.views import MetricDetail


urlpatterns = patterns(
    '',

    url(r'^(?P<schema>[0-9_a-zA-Z]+)/$',
        MetricDetail.as_view(),
        name='metric-detail'),

    url(r'^(?P<schema>[0-9_a-zA-Z]+)/(?P<metric_name>[0-9_a-zA-Z]+)/$',
        MetricDetail.as_view(),
        name='metric-detail'),

)

urlpatterns = format_suffix_patterns(urlpatterns)
