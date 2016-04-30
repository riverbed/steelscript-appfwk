# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
from collections import defaultdict

from rest_framework import serializers

from steelscript.appfwk.apps.metrics.models import NetworkMetric, ServicesMetric, \
    ServiceNode

logger = logging.getLogger(__name__)


SERIALIZER_MAP = defaultdict(dict)


def register_serializer(s, method='*'):
    """Add mapping of serializer `s` to associated model.

    Optionally specify associated method, (GET, POST, PUT, DELETE).  If not
    specified, will insert global mapping for all http methods.
    """
    global SERIALIZER_MAP
    SERIALIZER_MAP[s.Meta.model].update({method.lower(): s})


def find_serializer(m, method):
    """Given model `m` return associated serializer for given method.

    If '*' mapping included, will return that for any given method requested.
    """
    mapping = SERIALIZER_MAP[m]
    if '*' in mapping:
        return mapping['*']
    else:
        return mapping[method.lower()]


class BaseMetricSerializer(serializers.ModelSerializer):

    def restore_object(self, attrs, instance=None):
        """
        Handle how incoming data should be mapped into a model instance.
        """
        instance = super(BaseMetricSerializer, self).restore_object(attrs, instance=instance)

        if instance is not None:
            logger.debug('processing with instance method')
            instance.process_data(attrs)

        return instance

    def save_object(self, obj, **kwargs):
        return super(BaseMetricSerializer, self).save_object(obj, **kwargs)


#
# Custom Metrics - goes in plugin
#
from rest_framework import serializers


class SeparatedValuesSerializerField(serializers.Field):
    def field_from_native(self, data, files, field_name, into):
        """
        Override base class method:
        Given a dictionary and a field name, updates the dictionary `into`,
        with the field and it's deserialized value.
        """
        n = set([self.context[field_name]] or [])
        n.add(data[field_name])
        #into[field_name] = [data.get(field_name)]
        into[field_name] = list(n)
        return

    def field_to_native(self, obj, fieldname):
        """
        Override base class method:
        Given and object and a field name, returns the value that should be
        serialized for that field.
        """
        # converts list to list
        data = getattr(obj, fieldname, [])
        return data


class NetworkMetricSerializer(BaseMetricSerializer):
    class Meta:
        model = NetworkMetric

register_serializer(NetworkMetricSerializer)


class ServiceNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceNode
        fields = ('name',)

    def to_native(self, value):
        return value.name


class HybridPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    """Serialize out as PK, in will get_or_create new object."""
    def to_internal_value(self, data):
        return self.get_queryset().get_or_create(pk=data)

    def from_native(self, data):
        s = ServicesMetric.objects.get(name=self.context['name'])
        obj, created = self.queryset.get_or_create(pk=data, service=s)
        if created:
            logger.debug('Created new ServiceNode %s' % obj)
        else:
            logger.debug('Found existing ServiceNode %s' % obj)

        return super(HybridPrimaryKeyRelatedField, self).from_native(data)


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
