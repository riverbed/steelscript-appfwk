# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.devices.models import Device


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'module', 'host', 'port')

admin.site.register(Device, DeviceAdmin)
