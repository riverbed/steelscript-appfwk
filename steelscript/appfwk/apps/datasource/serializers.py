# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from rest_framework import serializers
from steelscript.appfwk.apps.datasource.models import \
    Table, TableField, Column, Job


#
# Field serializers
#
class PickledObjectField(serializers.Field):
    def field_to_native(self, obj, fieldname):
        # attempt to recurse through object and get json-able values out
        # we want to force for class obj, since they won't encode otherwise

        # try attr and fallback to dict access
        if hasattr(obj, 'get'):
            field = obj.get(fieldname, None)
        else:
            field = getattr(obj, fieldname)

        if field:
            if hasattr(field, 'iteritems'):
                for k, v in field.iteritems():
                    field[k] = self.field_to_native(field, k)
            else:
                if not isinstance(field, (str, unicode)):
                    # XXX do we want repr or str?
                    field = str(field)
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
class TableSerializer(serializers.HyperlinkedModelSerializer):
    options = PickledObjectField()
    criteria = PickledObjectField()
    fields = serializers.HyperlinkedRelatedField(
        many=True,
        view_name='table-field-detail'
    )

    class Meta:
        model = Table
        fields = ('url', 'name', 'module', 'queryclass', 'datasource',
                  'namespace', 'sourcefile', 'filterexpr', 'options',
                  'criteria', 'fields')


class TableFieldSerializer(serializers.HyperlinkedModelSerializer):
    initial = PickledObjectField()
    field_cls = PickledObjectField()
    field_kwargs = PickledObjectField()

    class Meta:
        model = TableField
        view_name = 'table-field-detail'
        fields = ("url", "keyword", "label", "help_text", "initial",
                  "required", "hidden", "field_cls", "field_kwargs",
                  "parent_keywords", "pre_process_func", "dynamic",
                  "post_process_func", "post_process_template")


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
