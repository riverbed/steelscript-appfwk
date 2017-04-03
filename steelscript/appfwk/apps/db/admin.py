# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.db.models import ExistingIntervals


class IntervalsAdmin(admin.ModelAdmin):
    list_display = ('namespace', 'sourcefile', 'table', 'criteria',
                    'existing_intervals', 'table_handle')

    def existing_intervals(self, obj):

        intervals = []
        for interval in obj.intervals:
            interval.localize_tz(obj.tzinfo)
            intervals.append(str(interval))
        return '<br>'.join(intervals)

    existing_intervals.allow_tags = True


admin.site.register(ExistingIntervals, IntervalsAdmin)
