# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from rest_framework import serializers
from steelscript.appfwk.apps.datasource.serializers import PickledObjectField
from steelscript.appfwk.apps.jobs.models import Job


class JobDataField(serializers.Field):
    def field_to_native(self, obj, fieldname):
        # calls values() on the Job object to get list of lists
        try:
            return obj.values()
        except AttributeError:
            # requesting data before its ready
            # XXX what is the best choice to do here?
            return {}


class JobSerializer(serializers.HyperlinkedModelSerializer):
    criteria = PickledObjectField()
    actual_criteria = PickledObjectField()

    # explicitly add these properties as fields
    status = serializers.Field()

    class Meta:
        model = Job
        fields = ('url', 'table', 'master', 'parent',
                  'criteria', 'actual_criteria', 'status',
                  'message',)
        read_only_fields = ('message',)


class JobListSerializer(JobSerializer):
    pass


class JobDetailSerializer(JobSerializer):
    pass


class JobDataSerializer(serializers.ModelSerializer):
    data = JobDataField()

    class Meta:
        model = Job
        fields = ('data',)
