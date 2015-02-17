# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from rest_framework import serializers

from steelscript.appfwk.apps.alerting.models import Alert, Event
from steelscript.appfwk.apps.datasource.serializers import JobSerializer


class PickledObjectField(serializers.Field):
    def to_native(self, value):
        return self.parent.to_native(value)

    def field_to_native(self, obj, fieldname):
        field = getattr(obj, fieldname)
        if field and 'func' in field:
            field['func'] = repr(field['func'])
        return field


class EventSerializer(serializers.HyperlinkedModelSerializer):
    alerts = serializers.HyperlinkedRelatedField(many=True,
                                                 view_name='alert-detail')
    context = PickledObjectField()
    trigger_result = PickledObjectField()

    def transform_context(self, obj, value):
        if 'job' in value:
            value['job'] = JobSerializer(value['job']).data
        return value

    class Meta:
        model = Event
        fields = ('url', 'timestamp', 'eventid', 'severity', 'log_message',
                  'context', 'trigger_result', 'alerts')


class AlertSerializer(serializers.HyperlinkedModelSerializer):
    options = PickledObjectField()
    event = serializers.HyperlinkedRelatedField(view_name='event-detail')

    class Meta:
        model = Alert
        fields = ('url', 'timestamp', 'event', 'level', 'sender',
                  'options', 'message')
