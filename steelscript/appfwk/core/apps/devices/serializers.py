from rest_framework import serializers
from steelscript.appfwk.core.apps.devices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device