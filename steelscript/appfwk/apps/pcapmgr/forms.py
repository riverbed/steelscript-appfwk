# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django import forms
from models import PcapDataFile


class PcapFileForm(forms.ModelForm):
    class Meta:
        model = PcapDataFile
        fields = ('description', 'datafile', 'file_type',
                  'start_time', 'end_time', 'pkt_count',)


class PcapFileListForm(forms.ModelForm):
    class Meta:
        model = PcapDataFile
        fields = ('description', 'datafile', 'file_type',
                  'start_time', 'end_time', 'pkt_count',)
