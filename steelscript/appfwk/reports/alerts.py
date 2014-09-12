# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3

from steelscript.appfwk.apps.datasource.modules.alerting import (AlertTable,
                                                                 AlertAnalysisGroupbyTable,
                                                                 AlertAnalysisTimeseriesTable)


report = Report.create('App Framework Alerts')

report.add_section()

atable = AlertTable.create('Appfwk Alerts')
atable.add_column('timestamp', 'Timestamp', datatype='time',
                  iskey=True, sortasc=True)
atable.add_column('id', 'ID', datatype='string')
atable.add_column('level', 'Level', datatype='string')
atable.add_column('router', 'Router', datatype='string')
atable.add_column('destination', 'Destination', datatype='string')
atable.add_column('message', 'Message', datatype='string')

report.add_widget(yui3.TableWidget, atable, 'App Framework Alerts', width=12)

attable = AlertAnalysisTimeseriesTable.create('Appfwk Alert Timeseries')
attable.add_column('timestamp', 'Timestamp', datatype='time', iskey=True)
attable.add_column('id', 'Number of Alerts', datatype='integer')

report.add_widget(yui3.TimeSeriesWidget, attable,
                  'App Framework Alerts Over Time', width=122)

agtable = AlertAnalysisGroupbyTable.create('Appfwk Alert Pie')
agtable.add_column('level', 'Level', datatype='string', iskey=True)
agtable.add_column('id', 'Count of Level', datatype='integer', sortasc=True)

report.add_widget(yui3.PieWidget, agtable,
                  'App Framework Alert Levels Pie', width=6)
report.add_widget(yui3.BarWidget, agtable,
                  'App Framework Alert Levels Bar', width=6)
