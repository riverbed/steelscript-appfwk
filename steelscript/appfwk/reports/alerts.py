# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.c3 as c3
import steelscript.appfwk.apps.report.modules.tables as tables
from steelscript.appfwk.apps.datasource.modules import alerting

report = Report.create('App Framework Alerts', position=11)

report.add_section()

atable = alerting.AlertHyperlinkedTable.create('Appfwk Alerts')
atable.add_column('timestamp', 'Timestamp', datatype='time',
                  iskey=True, sortdesc=True)
atable.add_column('id', 'ID', datatype='html')
atable.add_column('eventid', 'Event ID', datatype='html')
atable.add_column('level', 'Level', datatype='string')
atable.add_column('severity', 'Severity', datatype='integer')
atable.add_column('sender', 'Sender', datatype='string')
atable.add_column('options', 'Dest Options', datatype='html')
atable.add_column('message', 'Message', datatype='string')

report.add_widget(tables.TableWidget, atable, 'App Framework Alerts', width=12)

attable = alerting.AlertAnalysisTimeseriesTable.create('Alert Timeseries')
attable.add_column('timestamp', 'Timestamp', datatype='time', iskey=True)
attable.add_column('id', 'Number of Alerts', datatype='integer')

report.add_widget(c3.TimeSeriesWidget, attable,
                  'App Framework Alerts Over Time', width=12)

agtable = alerting.AlertAnalysisGroupbyTable.create('Appfwk Alert Pie')
agtable.add_column('level', 'Level', datatype='string', iskey=True)
agtable.add_column('id', 'Count of Level', datatype='integer', sortasc=True)
report.add_widget(c3.PieWidget, agtable, 'Alert Levels Pie', width=6)
report.add_widget(c3.BarWidget, agtable, 'Alert Levels Bar', width=6)

astable = alerting.AlertAnalysisGroupbyTable.create('Appfwk Alert Severity')
astable.add_column('severity', 'Severity', datatype='string', iskey=True)
astable.add_column('id', 'Count of Level', datatype='integer', sortasc=True)
report.add_widget(c3.PieWidget, astable, 'Alert Severity Pie', width=6)
report.add_widget(c3.BarWidget, astable, 'Alert Severity Bar', width=6)
