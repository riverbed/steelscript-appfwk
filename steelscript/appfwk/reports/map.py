# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.maps as maps
import steelscript.appfwk.apps.report.modules.yui3 as yui3
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerGroupbyTable

#
# Google Map example
#

report = Report.create("Response Time Map", position=10)

report.add_section()

# Define a map and table, group by location
p = NetProfilerGroupbyTable.create('maploc2', groupby='host_group', duration=60)

p.add_column('group_name', iskey=True, label='Group Name', datatype='string')
p.add_column('response_time', label='Resp Time', units='ms')
p.add_column('network_rtt', label='Net RTT', units='ms')
p.add_column('server_delay', label='Srv Delay', units='ms')
p.add_column('avg_bytes', label='Response Time', units='B/s')
p.add_column('peak_bytes', 'Peak Bytes/s', units='B/s')
p.add_column('avg_bytes_rtx', 'Avg Retrans Bytes/s', units='B/s')
p.add_column('peak_bytes_rtx', 'Peak Retrans Bytes/s', units='B/s')

# Create a Map widget
report.add_widget(maps.MapWidget, p, "Response Time Map", width=12,
                  height=500)

# Create a Table showing the same data as the map
report.add_widget(yui3.TableWidget, p, "Locations", width=12)
