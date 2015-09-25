# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.jobs.models import Job


class JobAdmin(admin.ModelAdmin):
    list_display = ('table', 'status', 'progress', 'message')

admin.site.register(Job, JobAdmin)
