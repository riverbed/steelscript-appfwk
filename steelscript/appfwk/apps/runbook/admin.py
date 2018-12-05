# Copyright (c) 2018 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin
from ordered_model.admin import OrderedTabularInline

from steelscript.appfwk.apps.runbook.models import Workflow, Sequence


class SequenceThroughModelInline(OrderedTabularInline):
    model = Sequence
    fields = ('report', 'order', 'move_up_down_links',)
    readonly_fields = ('order', 'move_up_down_links',)
    extra = 1
    ordering = ('order',)


class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('title',)
    inlines = (SequenceThroughModelInline,)

    def get_urls(self):
        urls = super(WorkflowAdmin, self).get_urls()
        for inline in self.inlines:
            if hasattr(inline, 'get_urls'):
                urls = inline.get_urls(self) + urls
        return urls


admin.site.register(Workflow, WorkflowAdmin)
