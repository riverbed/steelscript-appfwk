# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.geolocation.models import Location, LocationIP


class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')

admin.site.register(Location, LocationAdmin)

class LocationIPAdmin(admin.ModelAdmin):
    list_display = ('location', 'address', 'mask')

admin.site.register(LocationIP, LocationIPAdmin)
