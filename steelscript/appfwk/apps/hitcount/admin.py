# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from django.contrib import admin
from visits.models import Visit


# Override the VisitAdmin defined and registered in 3rd-party "visits" package.
class VisitAdmin(admin.ModelAdmin):
    list_display = ['uri', 'visits']
    list_filter = ['uri']
    search_fields = ['uri']

admin.site.unregister(Visit)
admin.site.register(Visit, VisitAdmin)
