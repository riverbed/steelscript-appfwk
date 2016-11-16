# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.maps as maps
import steelscript.appfwk.apps.report.modules.c3 as c3
import steelscript.appfwk.apps.report.modules.tables as tables

from steelscript.netprofiler.appfwk.datasources.netprofiler import (NetProfilerGroupbyTable,
                                                                    NetProfilerTimeSeriesTable)
from steelscript.netshark.appfwk.datasources.netshark import NetSharkTable

#
# Overall report
#

report = Report.create("Overall",
                       position=9,
                       field_order=['endtime', 'netprofiler_filterexpr',
                                    'netshark_filterexpr'],
                       hidden_fields=['resolution', 'duration'])

report.add_section('Locations', section_keywords=['resolution', 'duration'])

# Define a map and table, group by location
p = NetProfilerGroupbyTable.create('maploc', groupby='host_group', duration=60,
                                   resolution='auto')

p.add_column('group_name', label='Group Name', iskey=True, datatype="string")
p.add_column('response_time', label='Resp Time',  units='ms', sortdesc=True)
p.add_column('network_rtt', label='Net RTT',    units='ms')
p.add_column('server_delay', label='Srv Delay',  units='ms')

# Adding a widget using the Report object will apply them
# to the last defined Section, here that will be 'Locations'
report.add_widget(c3.BarWidget, p, "Response Time", width=6, height=300)
report.add_widget(tables.TableWidget, p, "Locations by Response Time", width=6,
                  info=False, paging=False, searching=False)

# Define a Overall TimeSeries showing Avg Bytes/s
report.add_section('NetProfiler Overall',
                   section_keywords=['resolution', 'duration'])

p = NetProfilerTimeSeriesTable.create('ts1', duration=1440, resolution='15min')

p.add_column('time', label='Time', datatype='time', iskey=True)
p.add_column('avg_bytes', label='Avg Bytes/s', units='B/s')

report.add_widget(c3.TimeSeriesWidget, p,
                  "NetProfiler Overall Traffic", width=6)

# NetShark Time Series
section = report.add_section('NetShark Traffic',
                             section_keywords=['resolution', 'duration'])

shark = NetSharkTable.create('Total Traffic Bits', duration=15,
                             resolution='1sec', aggregated=False)

shark.add_column('time', extractor='sample_time', iskey=True,
                 label='Time', datatype='time')
shark.add_column('generic_bits', label='bits', iskey=False,
                 extractor='generic.bits', operation='sum', units='b')

# Widgets can also be added to Section objects explicitly
section.add_widget(c3.TimeSeriesWidget, shark,
                   'Overall Bandwidth (Bits) at (1-second resolution)',
                   width=6)
