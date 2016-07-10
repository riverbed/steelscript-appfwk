# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3
from steelscript.appfwk.apps.datasource.modules.metrics import MetricsTable


#
# Metrics Report
#

report = Report.create("Metrics Example", position=12)
report.add_section()

# ServicesMetrics
s = MetricsTable.create('services-metrics', schema='services', cacheable=False)
s.add_column('name', 'Service', datatype='string')
s.add_column('status_text', 'Status', datatype='string',
             formatter='rvbd.formatHealthWithHover')

report.add_widget(yui3.TableWidget, s, "Services Metrics", width=6)

# NetworkMetrics
m = MetricsTable.create('network-metrics', schema='network', cacheable=False)
m.add_column('location', 'Location', datatype='string')
m.add_column('Infrastructure', 'Infrastructure', datatype='string',
             formatter='rvbd.formatHealthWithHover')
m.add_column('LargeOffice', 'LargeOffice', datatype='string',
             formatter='rvbd.formatHealthWithHover')

report.add_widget(yui3.TableWidget, m, "Network Metrics", width=6)
