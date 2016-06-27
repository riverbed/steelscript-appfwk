# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from steelscript.appfwk.apps.metrics.serializers import BaseMetricSerializer, \
    register_serializer
from steelscript.appfwk.apps.plugins.builtin.metrics_plugin.models import \
    NetworkMetric, ServicesMetric

logger = logging.getLogger(__name__)


#
# Custom Metrics - Code below goes into plugin serializers.py
#

class ServicesMetricSerializer(BaseMetricSerializer):

    class Meta:
        model = ServicesMetric
        fields = ('name', 'node_name', 'node_status')

register_serializer(ServicesMetricSerializer, method='POST')


class ServicesMetricDetailSerializer(BaseMetricSerializer):

    class Meta:
        model = ServicesMetric
        fields = ('name', 'override_value', 'affected_nodes')

register_serializer(ServicesMetricDetailSerializer, method='GET')


class NetworkMetricSerializer(BaseMetricSerializer):
    class Meta:
        model = NetworkMetric
        fields = ('node_name', 'node_status', 'location',
                  'parent_group', 'parent_status')

register_serializer(NetworkMetricSerializer, method='POST')


class NetworkMetricDetailSerializer(BaseMetricSerializer):
    class Meta:
        model = NetworkMetric
        fields = ('location', 'parent_group',
                  'parent_status', 'affected_nodes')

register_serializer(NetworkMetricDetailSerializer, method='GET')
