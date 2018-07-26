# Copyright (c) 2018 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin
from steelscript.appfwk.apps.filemgr.models import DataFile


class FileAdmin(admin.ModelAdmin):
    list_display = ('datafile', 'description', 'uploaded_at',
                    'file_type', 'file_bytes',)


admin.site.register(DataFile, FileAdmin)
