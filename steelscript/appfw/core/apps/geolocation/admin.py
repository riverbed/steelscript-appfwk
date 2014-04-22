# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#  https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

from django.contrib import admin
from rvbd_portal.apps.geolocation.models import Location, LocationIP


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')

admin.site.register(Location, LocationAdmin)

class LocationIPAdmin(admin.ModelAdmin):
    list_display = ('location', 'address', 'mask')

admin.site.register(LocationIP, LocationIPAdmin)
