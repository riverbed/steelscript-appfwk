# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3

from steelscript.netprofiler.appfwk.datasources.netprofiler import (NetProfilerTimeSeriesTable,
                                                                    NetProfilerGroupbyTable)

report = Report.create("DSCP Report", position=11)

interface_field = TableField.create(keyword='interface', label='Interface',
                                    required=True)
datafilter_field = TableField.create(keyword='datafilter', hidden=True,
                                     post_process_template='interfaces_a,{interface}')

report.add_section("Overall")

# Define a Overall TimeSeries showing In/Out Utilization
p = NetProfilerTimeSeriesTable.create('dscp-overall-util',
                                      duration=15, resolution=60,
                                      interface=True)
p.fields.add(interface_field)
p.fields.add(datafilter_field)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_avg_util', 'Avg Inbound Util %', units='B/s')
p.add_column('out_avg_util', 'Avg Outbound Util %', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Overall Utilization", width=12)

# Define a Overall TimeSeries showing In/Out Totals
p = NetProfilerTimeSeriesTable.create('dscp-overall-total',
                                      duration=15, resolution=15 * 60,
                                      interface=True)
p.fields.add(interface_field)
p.fields.add(datafilter_field)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_total_bytes', 'Total Inbound Bytes', units='B/s')
p.add_column('out_total_bytes', 'Total Outbound Bytes', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p, "Overall In/Out Bandwidth",
                  width=6)

# Define a Overall TimeSeries showing In/Out Totals
p = NetProfilerTimeSeriesTable.create('dscp-overall-avg',
                                      duration=15, resolution=60,
                                      interface=True)
p.fields.add(interface_field)
p.fields.add(datafilter_field)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_avg_bytes', 'Avg Inbound Bytes/s', units='B/s')
p.add_column('out_avg_bytes', 'Avg Outbound Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, p,
                  "Overall Average In/Out Bandwidth", width=6)

# ##
# DSCP Summary Tables
for direction in ['inbound', 'outbound']:
    p = NetProfilerGroupbyTable.create('dscp-%s-totals' % direction,
                                       groupby='dsc',
                                       duration=15, resolution=60,
                                       interface=True)
    p.fields.add(interface_field)

    TableField.create(
        keyword='%s_filterexpr' % direction,
        obj=p,
        hidden=True,
        post_process_template='%s interface {interface}' % direction
    )
    p.fields_add_filterexprs_field('%s_filterexpr' % direction)

    p.add_column('dscp', 'DSCP', iskey=True)
    p.add_column('dscp_name', 'DSCP Name', iskey=True)
    p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
    p.add_column('total_bytes', 'Total Bytes/s', units='B/s')
    p.add_column('avg_util', 'Avg Util', units='pct')
    p.add_column('peak_util', 'Peak Util', units='pct')

    report.add_widget(yui3.TableWidget, p,
                      "%s Traffic by DSCP" % direction.capitalize(), width=6)

# ##
# DSCP sections, defaults to AF11, EF, and Default
for i, dscp in enumerate(['AF11', 'EF', 'Default']):

    report.add_section("DSCP %d" % i)

    # ##
    # DSCP Tables

    for direction in ['inbound', 'outbound']:
        p = NetProfilerTimeSeriesTable.create('dscp-%d-%s' % (i, direction),
                                              duration=15, resolution=60,
                                              interface=True)
        p.fields.add(interface_field)
        p.fields.add(datafilter_field)
        dscp_field = TableField.create(keyword='dscp_%d' % i,
                                       label='DSCP %d' % i, obj=p,
                                       initial=dscp)
        TableField.create(
            keyword='%s_filterexpr' % direction, obj=p,
            hidden=True,
            post_process_template=('%s interface {interface} and dscp {dscp_%d}'
                                   % (direction, i))
        )
        p.fields_add_filterexprs_field('%s_filterexpr' % direction)

        p.add_column('time', 'Time', datatype='time', iskey=True)
        p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

        report.add_widget(yui3.TimeSeriesWidget, p,
                          "DSCP {dscp_%d} - Average %s Bandwidth"
                          % (i, direction.capitalize()),
                          width=6)
