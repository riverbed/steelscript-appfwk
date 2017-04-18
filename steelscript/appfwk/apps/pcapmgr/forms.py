# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from os.path import basename
from django import forms
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.pcapmgr.models import PcapDataFile
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.datasource.forms import IntegerIDChoiceField


class PcapFileForm(forms.ModelForm):
    class Meta:
        model = PcapDataFile
        fields = ('description', 'datafile', 'file_type',
                  'start_time', 'end_time', 'pkt_count',
                  'packet_bytes',)


class PcapFileListForm(forms.ModelForm):
    class Meta:
        model = PcapDataFile
        fields = ('description', 'datafile', 'file_type',
                  'start_time', 'end_time', 'pkt_count',
                  'packet_bytes',)


def pcap_selection_preprocess(form, field, field_kwargs, params):
    pcap_mgr_files = PcapDataFile.objects.order_by('id')
    if pcap_mgr_files:
        choices = [(p.id, basename(p.datafile.name)) for p in pcap_mgr_files]
    else:
        choices = [('', '<No PCAP Manager files available>')]

    field_kwargs['choices'] = choices


def fields_add_pcapmgr_selection(obj,
                                 keyword='pcapmgrfile',
                                 label='PCAPMgrFile'):
    field = TableField(keyword=keyword, label=label,
                       field_cls=IntegerIDChoiceField,
                       pre_process_func=Function(pcap_selection_preprocess))
    field.save()
    obj.fields.add(field)
