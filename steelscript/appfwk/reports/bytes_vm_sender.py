# Copyright (c) 2014 Riverbed Technology, Inc.
#
# in the License. This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.alerting.models import create_trigger, create_destination
from steelscript.appfwk.apps.alerting.datastructures import Results
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerTimeSeriesTable,\
                                                                   NetProfilerGroupbyTable

import steelscript.appfwk.apps.report.modules.yui3 as yui3

report = Report.create("NetProfiler-Bytes", position=10)

report.add_section()


# Define a Overall TimeSeries showing Avg Bytes/s
table = NetProfilerTimeSeriesTable.create('VMSenderDemo', duration=60, resolution="1min")

table.add_column('time', 'Time', datatype='time', iskey=True)
table.add_column('avg_bytes', 'Avg Bytes/s', units='B/s')

report.add_widget(yui3.TimeSeriesWidget, table, "Netprofiler Traffic", width=12)


# Define a trigger function
def bytes_trigger(x, context, params):
    return Results().add_result((x['avg_bytes'] > 0.01).any(), severity=15)


a = create_trigger(source=table,
                   trigger_func=bytes_trigger)


a.add_destination(sender='BareMetalVMSender',
                  options={'host' : 'host',
                             'username': 'user',
                             'password': 'pswd',
                             'vagrant_dir': 'directory', 
                             'up_list': ['vm1'],
                             'down_list': ['vm2']},
                  template = 'Starting or shutting vms'
                  )
