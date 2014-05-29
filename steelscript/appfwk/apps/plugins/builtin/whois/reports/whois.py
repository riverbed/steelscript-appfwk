# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.plugins.builtin.whois.datasource.whois import WhoisTable

from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerGroupbyTable
from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.yui3 as yui3

# helper libraries

#
# NetProfiler report
#

report = Report.create("Whois", position=11)

report.add_section()

# Define a Table that gets external hosts by avg bytes
table = NetProfilerGroupbyTable.create('5-hosts', groupby='host', duration='1 hour',
                                    filterexpr='not srv host 10/8 and not srv host 192.168/16')

table.add_column('host_ip', 'IP Addr', iskey=True, datatype='string')
table.add_column('avg_bytes', 'Avg Bytes', units='B/s', sortdesc=True)


#report.add_widget(yui3.TableWidget, table, "Table", width=12)

# Create an Analysis table that calls the 'whois' function to craete a link to
# 'whois'
whoistable = WhoisTable.create('5-whois-hosts',
                               tables={'t': table})

report.add_widget(yui3.TableWidget, whoistable, "Link table", width=12)
