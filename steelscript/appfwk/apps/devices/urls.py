# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns

from steelscript.appfwk.apps.devices.views import DeviceList, DeviceDetail,\
    DeviceBatch


urlpatterns = patterns(
    '',

    url(r'^$',
        DeviceList.as_view(),
        name='device-list'),

    url(r'^(?P<device_id>[0-9]+)/$',
        DeviceDetail.as_view(),
        name='device-detail'),

    url(r'^add/$',
        DeviceDetail.as_view(),
        name='device-add'),

    url(r'batch/$',
        DeviceBatch.as_view(),
        name='device-batch')

)

urlpatterns = format_suffix_patterns(urlpatterns)
