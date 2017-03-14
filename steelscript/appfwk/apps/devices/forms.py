# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django import forms
from django.forms import FileInput

from steelscript.common import Auth
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.devices.models import Device
from steelscript.appfwk.apps.devices.devicemanager import DeviceManager
from steelscript.appfwk.apps.datasource.forms import IntegerIDChoiceField
from steelscript.appfwk.apps.datasource.forms import FileSelectField, \
    TableFieldForm


class DeviceForm(forms.ModelForm):

    class Meta:
        model = Device
        fields = ('name', 'module', 'host', 'port', 'auth',
                  'username', 'password', 'access_code', 'enabled', 'tags')

        widgets = {'auth': forms.HiddenInput(),
                   'username': forms.HiddenInput(),
                   'password': forms.HiddenInput(),
                   'access_code': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)

    def clean(self):
        # field validation only really matters if the device was enabled
        cleaned_data = super(DeviceForm, self).clean()
        enabled = cleaned_data.get('enabled')

        if enabled:
            if cleaned_data.get('auth', '') == Auth.BASIC:
                if cleaned_data.get('username', '') == '':
                    msg = u'Please enter a valid username.'
                    self._errors['username'] = self.error_class([msg])
                    cleaned_data.pop('username', None)

                if cleaned_data.get('password', '') == '':
                    msg = u'Please enter a valid password.'
                    self._errors['password'] = self.error_class([msg])
                    cleaned_data.pop('password', None)

            elif cleaned_data.get('auth', '') == Auth.OAUTH:
                if cleaned_data.get('access_code', '') == '':
                    msg = u'Please enter a valid access code.'
                    self._errors['access_code'] = self.error_class([msg])
                    cleaned_data.pop('access_code', None)

        # Check if already exist device with same host/port when adding device
        if not self.instance.host:
            # To add a device
            if Device.objects.filter(host=cleaned_data['host'],
                                     port=cleaned_data['port']):
                msg = "Found device(s) with same host-port pair."
                self._errors['port'] = self.error_class([msg])

        return cleaned_data


class DeviceListForm(forms.ModelForm):
    """ Used for displaying existing Devices in a list view
    """
    class Meta:
        model = Device
        fields = ('enabled', )


class DeviceDetailForm(DeviceForm):
    """ Used for creating new Devices, or editing existing ones
    """
    def __init__(self, *args, **kwargs):
        super(DeviceDetailForm, self).__init__(*args, **kwargs)

        modules = DeviceManager.get_modules()
        choices = zip(modules, modules)

        self.fields['module'] = forms.ChoiceField(
            choices=choices,
            widget=forms.Select(attrs={"onChange": 'changeMod()'}))


def fields_add_device_selection(obj, keyword='device',
                                label='Device',
                                module=None, enabled=None):
    field = TableField(keyword=keyword, label=label,
                       field_cls=IntegerIDChoiceField,
                       pre_process_func=Function(device_selection_preprocess,
                                                 {'module': module,
                                                  'enabled': enabled}))
    field.save()
    obj.fields.add(field)


def device_selection_preprocess(form, field, field_kwargs, params):
    filter_ = {}
    for k in ['module', 'enabled']:
        if k in params and params[k] is not None:
            filter_[k] = params[k]

    devices = Device.objects.filter(**filter_)
    if len(devices) == 0:
        choices = [('', '<No devices available>')]
    else:
        choices = [(d.id, d.name) for d in devices]

    field_kwargs['choices'] = choices


class DeviceBatchForm(TableFieldForm):

    def __init__(self, *args, **kwargs):
        fields = {}

        res = TableField.objects.filter(keyword='batch_file')

        if not res:
            file_upload = TableField(keyword='batch_file',
                                     label='Batch File',
                                     field_cls=FileSelectField,
                                     field_kwargs=dict(widget=FileInput),
                                     required=True)
            file_upload.save()
        else:
            file_upload = res[0]

        fields['batch_file'] = file_upload

        super(DeviceBatchForm, self).__init__(fields, *args, **kwargs)
