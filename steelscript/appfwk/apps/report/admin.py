# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.report.models import Report, Widget, WidgetJob


class ReportAdmin(admin.ModelAdmin):
    list_display = ('enabled', 'title', 'position', 'namespace',
                    'sourcefile', 'slug')
    fieldsets = (
        (None, {
            'fields': ('title', 'position', 'enabled', 'slug',
                       'namespace', 'sourcefile', 'field_order',
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
    actions = ['mark_enabled', 'mark_disabled']

    def mark_disabled(self, request, queryset):
        queryset.update(enabled=False)
    mark_disabled.short_description = 'Mark selected reports disabled'

    def mark_enabled(self, request, queryset):
        queryset.update(enabled=True)
    mark_enabled.short_description = 'Mark selected reports enabled'

admin.site.register(Report, ReportAdmin)


class WidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'section', 'module', 'uiwidget')
    list_filter = ('section', 'module', 'uiwidget', )

#admin.site.register(Widget, WidgetAdmin)


class WidgetJobAdmin(admin.ModelAdmin):
    pass

#admin.site.register(WidgetJob, WidgetJobAdmin)
