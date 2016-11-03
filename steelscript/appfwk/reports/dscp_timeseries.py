# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.c3 as c3
import steelscript.appfwk.apps.report.modules.tables as tables

from steelscript.netprofiler.appfwk.datasources.netprofiler import \
    NetProfilerTimeSeriesTable, NetProfilerGroupbyTable, NetProfilerTable

report = Report.create("DSCP Report", position=10,
                       hidden_fields=['netprofiler_filterexpr'])

netprofiler_filterexpr = TableField.create(
    keyword='netprofiler_filterexpr')

interface_field = TableField.create(
    keyword='interface', label='Interface', required=True)

#
# Overall section
#  - netprofiler_filterexpr = "interface {interface}"
#
section = report.add_section("Overall",
                             section_keywords=['netprofiler_filterexpr',
                                               'interface_expr'])

section.fields.add(netprofiler_filterexpr)
section.fields.add(interface_field)

NetProfilerTable.extend_filterexpr(section, keyword='interface_filterexpr',
                                   template='interface {interface}')

# Define a Overall TimeSeries showing In/Out Utilization
p = NetProfilerTimeSeriesTable.create('qos-overall-util',
                                      duration=15, resolution=60,
                                      interface=True)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_avg_util', 'Avg Inbound Util %', units='B/s')
p.add_column('out_avg_util', 'Avg Outbound Util %', units='B/s')

report.add_widget(c3.TimeSeriesWidget, p, "{interface} - Overall Utilization",
                  width=12)

# Define a Overall TimeSeries showing In/Out Totals
p = NetProfilerTimeSeriesTable.create('qos-overall-total',
                                      duration=15, resolution=15 * 60,
                                      interface=True)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_total_bytes', 'Total Inbound Bytes', units='B/s')
p.add_column('out_total_bytes', 'Total Outbound Bytes', units='B/s')

report.add_widget(c3.TimeSeriesWidget, p, "Overall In/Out Totals",
                  width=6)

# Define a Overall TimeSeries showing In/Out Totals
p = NetProfilerTimeSeriesTable.create('qos-overall-avg',
                                      duration=15, resolution=60,
                                      interface=True)

p.add_column('time', 'Time', datatype='time', iskey=True)
p.add_column('in_avg_bytes', 'Avg Inbound B/s', units='B/s')
p.add_column('out_avg_bytes', 'Avg Outbound B/s', units='B/s')

report.add_widget(c3.TimeSeriesWidget, p,
                  "Overall In/Out Avg BW ", width=6)

#
# QOS Summary Tables
#
for direction in ['inbound', 'outbound']:
    #
    # Section per direction
    #  - netprofiler_filterexpr = "{direction} interface {interface}"
    #    - direction is hardcoded from the loop
    #    - interface comes from the field
    #
    section = report.add_section("%s" % direction,
                                 section_keywords=['netprofiler_filterexpr',
                                                   'interface_expr'])

    section.fields.add(netprofiler_filterexpr)
    section.fields.add(interface_field)

    NetProfilerTable.extend_filterexpr(
        section, keyword='interface_filterexpr',
        template=('%s interface {interface}' % direction))

    p = NetProfilerGroupbyTable.create('qos-%s-totals' % direction,
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

    p.add_column('dscp', 'Dscp', iskey=True, datatype="integer")
    p.add_column('dscp_name', 'Dscp Name', iskey=True, datatype="string")
    p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')
    p.add_column('total_bytes', 'Total Bytes/s', units='B/s')
    p.add_column('avg_util', 'Avg Util', units='pct')
    p.add_column('peak_util', 'Peak Util', units='pct')

    report.add_widget(tables.TableWidget, p,
                      "%s Traffic by DSCP" % direction.capitalize(), width=6)

#
# Dscp sections, defaults to AF11, EF, and Default
#
for i, dscp in enumerate(['AF11', 'EF', 'Default']):

    report.add_section("DSCP %d" % i)

    for direction in ['inbound', 'outbound']:
        #
        # Section per direction
        #  - netprofiler_filterexpr = "{direction} interface {interface}"
        #    - direction is hardcoded from the loop
        #    - interface comes from the field
        #
        section = report.add_section(
            "%s %s" % (direction, dscp),
            section_keywords=['netprofiler_filterexpr',
                              'interface_expr'])

        section.fields.add(netprofiler_filterexpr)
        section.fields.add(interface_field)

        NetProfilerTable.extend_filterexpr(
            section, keyword='interface_filterexpr',
            template=(
                'set any [%s interface {interface}] with set any [dscp %s]' %
                (direction, dscp)
            )
        )

        p = NetProfilerTimeSeriesTable.create('qos-%d-%s' % (i, direction),
                                              duration=15, resolution=60,
                                              interface=True)

        p.add_column('time', 'Time', datatype='time', iskey=True)
        p.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

        report.add_widget(
            c3.TimeSeriesWidget, p,
            "%s - %s Avg BW" % (dscp, direction.capitalize()),
            width=6)
