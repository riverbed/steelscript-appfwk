# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin
from steelscript.appfwk.apps.pcapmgr.models import PcapDataFile


class PcapFileAdmin(admin.ModelAdmin):
    list_display = ('datafile', 'description', 'uploaded_at',
                    'file_type', 'start_time', 'end_time',
                    'pkt_count', 'packet_bytes', )


admin.site.register(PcapDataFile, PcapFileAdmin)
