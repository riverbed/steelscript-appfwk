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
        #field = dbsafe_decode(field)
        if field and 'func' in field:
            field['func'] = repr(field['func'])
        return field


class JobDataField(serializers.Field):
    def field_to_native(self, obj, fieldname):
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

    class Meta:
        model = Table


class ColumnSerializer(serializers.ModelSerializer):
    options = PickledObjectField()

    class Meta:
        model = Column
        fields = ('id', 'name', 'label', 'position', 'options', 'iskey',
                  'synthetic', 'datatype', 'units')


class JobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ('id', 'table', 'criteria', 'actual_criteria', 'status', 'message', 'progress', 'remaining')
        read_only_fields = ('id', 'status', 'message', 'progress', 'remaining')


class JobSerializer(serializers.ModelSerializer):
    criteria = PickledObjectField()
    actual_criteria = PickledObjectField()

    class Meta:
        model = Job
        fields = ('id', 'table', 'criteria', 'actual_criteria', 'status', 'message', 'progress', 'remaining')
        read_only_fields = ('id', 'status', 'message', 'progress', 'remaining')


class JobDataSerializer(serializers.ModelSerializer):
    data = JobDataField()

    class Meta:
        model = Job
        fields = ('data',)
