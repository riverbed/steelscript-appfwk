# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import os

from django.contrib import admin
from django.core import management
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from steelscript.appfwk.apps.report.models import Report, WidgetAuthToken


class ReportAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'title', 'position', 'namespace',
                    'sourcefile', 'filepath', 'slug')
    fieldsets = (
        (None, {
            'fields': ('title', 'position', 'enabled', 'slug',
                       'namespace', 'sourcefile', 'filepath', 'field_order',
                       'hidden_fields')
        }),
        ('Auto Reports', {
            'fields': ('hide_criteria', 'reload_minutes')
        }),
        ('Report Fields', {
            'classes': ('collapse',),
            'fields': ('fields',)
        })
    )
    filter_horizontal = ('fields',)
    actions = ['delete_modelset', 'mark_enabled', 'mark_disabled',
               'edit_report']

    def mark_disabled(self, request, queryset):
        queryset.update(enabled=False)
    mark_disabled.short_description = 'Mark selected reports disabled'

    def mark_enabled(self, request, queryset):
        queryset.update(enabled=True)
    mark_enabled.short_description = 'Mark selected reports enabled'

    def edit_report(self, request, queryset):
        return HttpResponseRedirect(reverse('report-editor',
                                    args=(queryset[0].namespace,
                                          queryset[0].slug)))
    edit_report.short_description = ('Edit selected report '
                                     '(first selection only)')

    def delete_modelset(self, request, queryset):
        for report in queryset:
            management.call_command('clean',
                                    applications=False,
                                    report_id=report.id,
                                    clear_cache=False,
                                    clear_logs=False)
            try:
                os.unlink(report.filepath)
                msg = 'Report %s and file %s deleted' % (report.title,
                                                         report.filepath)
                messages.add_message(request, messages.INFO, msg)
            except IOError:
                msg = 'Error deleting file %s' % report.filepath
                messages.add_message(request, messages.ERROR, msg)
    delete_modelset.short_description = 'Delete reports and their source files'

admin.site.register(Report, ReportAdmin)


class WidgetAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'user', 'pre_url', 'criteria', 'touched')
    list_filter = ('user', 'pre_url', 'touched')
    search_fields = ('user__username', 'pre_url')
    readonly_fields = ('touched', 'criteria')
    fields = ('token', 'user', 'pre_url', 'criteria', 'touched')

admin.site.register(WidgetAuthToken, WidgetAuthTokenAdmin)


class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'module', 'uiwidget')
    list_filter = ('section', 'module', 'uiwidget', )

#admin.site.register(Widget, WidgetAdmin)


class WidgetJobAdmin(admin.ModelAdmin):
    pass

#admin.site.register(WidgetJob, WidgetJobAdmin)
