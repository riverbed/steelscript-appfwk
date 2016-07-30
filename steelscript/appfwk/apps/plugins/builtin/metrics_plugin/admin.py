# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from .models import NetworkMetric, ServicesMetric, ServiceNode, NetworkNode


#
# Include in plugin admin.py
#
class NetworkNodeInline(admin.TabularInline):
    model = NetworkNode
    fields = ('name',)


class NetworkMetricAdmin(admin.ModelAdmin):
    list_display = ('location', 'parent_group', 'parent_status',
                    'override_value', 'affected_nodes')
    fields = ('location', 'parent_group', 'parent_status', 'override_value')
    inlines = (NetworkNodeInline,)
    ordering = ('id', )

    def affected_nodes(self, obj):
        return obj.affected_nodes.all()

admin.site.register(NetworkMetric, NetworkMetricAdmin)


class ServiceNodeInline(admin.TabularInline):
    model = ServiceNode
    fields = ('name',)


class ServicesMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'override_value', 'affected_nodes')
    inlines = (ServiceNodeInline,)
    ordering = ('id', )

    def affected_nodes(self, obj):
        return obj.affected_nodes.all()

admin.site.register(ServicesMetric, ServicesMetricAdmin)
