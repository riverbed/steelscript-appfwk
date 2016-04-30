# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.contrib import admin

from steelscript.appfwk.apps.metrics.models import Metric, NetworkMetric, ServicesMetric, \
    ServiceNode


class MetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'override_value')


class NetworkMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'override_value')

admin.site.register(NetworkMetric, NetworkMetricAdmin)


class ServiceNodeInline(admin.TabularInline):
    model = ServiceNode
    fields = ('name',)


class ServicesMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'override_value', 'affected_nodes')
    inlines = (ServiceNodeInline,)

    def affected_nodes(self, obj):
        return obj.affected_nodes.all()

admin.site.register(ServicesMetric, ServicesMetricAdmin)
