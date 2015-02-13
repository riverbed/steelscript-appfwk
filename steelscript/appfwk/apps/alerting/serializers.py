# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from rest_framework import serializers

from steelscript.appfwk.libs.fields import PickledObjectField
from steelscript.appfwk.apps.alerting.models import Alert, Event


class EventSerializer(serializers.ModelSerializer):
    alerts = serializers.PrimaryKeyRelatedField(many=True)
    context = PickledObjectField()
    trigger_result = PickledObjectField()

    class Meta:
        model = Event
        fields = ('id', 'timestamp', 'eventid', 'severity', 'log_message',
                  'context', 'trigger_result', 'alerts')


class AlertSerializer(serializers.ModelSerializer):
    options = PickledObjectField()
    event = serializers.Field(source='event')

    class Meta:
        model = Alert
        fields = ('id', 'timestamp', 'event', 'level', 'sender',
                  'options', 'message')
