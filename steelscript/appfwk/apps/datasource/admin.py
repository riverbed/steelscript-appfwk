# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.datasource.models import Table, Column, TableField


class TableAdmin(admin.ModelAdmin):
    list_display = ('name', 'module')
    list_filter = ('module', )

admin.site.register(Table, TableAdmin)


class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'table', 'iskey')
    list_filter = ('table', )

admin.site.register(Column, ColumnAdmin)


class TableFieldAdmin(admin.ModelAdmin):
    list_display = (
        'label', 'help_text', 'initial', 'required',
        'hidden', 'field_cls', 'field_kwargs',  'parent_keywords',
        'pre_process_func', 'post_process_func', 'post_process_template',
    )

admin.site.register(TableField, TableFieldAdmin)
