# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from rest_framework import serializers
from steelscript.appfwk.apps.datasource.models import Table, Column, Job


#
# Field serializers
#
class PickledObjectField(serializers.Field):
    def field_to_native(self, obj, fieldname):
        field = getattr(obj, fieldname)
        if field and 'func' in field:
            field['func'] = repr(field['func'])
        return field


class JobDataField(serializers.Field):
    def field_to_native(self, obj, fieldname):
        # calls values() on the Job object to get list of lists
        try:
            return obj.values()
        except AttributeError:
            # requesting data before its ready
            # XXX what is the best choice to do here?
            return {}


#
# Model serializers
#
class TableSerializer(serializers.ModelSerializer):
    options = PickledObjectField()
    criteria = PickledObjectField()

    class Meta:
        model = Table
        fields = ('id', 'name', 'module', 'queryclass', 'datasource',
                  'namespace', 'sourcefile', 'filterexpr', 'options',
                  'criteria', 'fields')


class ColumnSerializer(serializers.ModelSerializer):
    options = PickledObjectField()

    class Meta:
        model = Column
        fields = ('id', 'name', 'label', 'position', 'options', 'iskey',
                  'synthetic', 'datatype', 'units')


class JobListSerializer(serializers.HyperlinkedModelSerializer):
    criteria = PickledObjectField()
    actual_criteria = PickledObjectField()

    class Meta:
        model = Job
        fields = ('url', 'table', 'criteria', 'actual_criteria', 'status',
                  'message', 'progress', 'remaining')
        read_only_fields = ('status', 'message', 'progress', 'remaining')


class JobSerializer(serializers.HyperlinkedModelSerializer):
    criteria = PickledObjectField()
    actual_criteria = PickledObjectField()

    class Meta:
        model = Job
        fields = ('url', 'table', 'criteria', 'actual_criteria', 'status',
                  'message', 'progress', 'remaining')
        read_only_fields = ('status', 'message', 'progress', 'remaining')

    def save(self, **kwargs):
        return super(JobSerializer, self).save(**kwargs)


class JobDataSerializer(serializers.ModelSerializer):
    data = JobDataField()

    class Meta:
        model = Job
        fields = ('data',)
