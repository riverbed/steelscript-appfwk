# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django import forms

from steelscript.netprofiler.core import _constants
from steelscript.appfwk.apps.devices.models import Device


def get_device_choices(device_type):
    devices = Device.objects.filter(module=device_type)
    return [(d.id, d.name) for d in devices]


def get_groupbys():
    return [('', '---')] + sorted(((v, k) for k,v in _constants.groupbys.iteritems()))


def get_realms():
    return [('', '---')] + [(c, c.title().replace('_', ' ')) for c in _constants.realms]


def get_centricities():
    return ('', '---'), ('hos', 'host'), ('int', 'interface')


class NetProfilerInputForm(forms.Form):
    device = forms.ChoiceField(choices=get_device_choices('netprofiler'))
    realm = forms.ChoiceField(choices=get_realms())
    centricity = forms.ChoiceField(choices=get_centricities())
    groupby = forms.ChoiceField(choices=get_groupbys())


class NetSharkInputForm(forms.Form):
    device = forms.ChoiceField(choices=get_device_choices('netshark'))
