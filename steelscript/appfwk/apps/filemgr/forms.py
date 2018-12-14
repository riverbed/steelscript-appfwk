# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from os.path import basename
from django import forms
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.filemgr.models import DataFile
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.datasource.forms import IntegerIDChoiceField


class DataFileForm(forms.ModelForm):
    class Meta:
        model = DataFile
        fields = ('description', 'datafile', 'file_type', 'file_bytes',)


class DataFileListForm(forms.ModelForm):
    class Meta:
        model = DataFile
        fields = ('description', 'datafile', 'file_type', 'file_bytes',)


def file_selection_preprocess(form, field, field_kwargs, params):
    file_mgr_files = DataFile.objects.order_by('id')
    if file_mgr_files:
        choices = [(p.id, basename(p.datafile.name)) for p in file_mgr_files]
    else:
        choices = [('', '<No File Manager files available>')]

    field_kwargs['choices'] = choices


def fields_add_filemgr_selection(obj,
                                 keyword='filemgrfile',
                                 label='FileMgrFile'):
    field = TableField(keyword=keyword, label=label,
                       field_cls=IntegerIDChoiceField,
                       pre_process_func=Function(file_selection_preprocess))
    field.save()
    obj.fields.add(field)
