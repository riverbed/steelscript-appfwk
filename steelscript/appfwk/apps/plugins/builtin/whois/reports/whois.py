# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.plugins.builtin.whois.datasource.whois import \
    WhoisTable, whois_function

from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.netprofiler.appfwk.datasources.netprofiler import \
    NetProfilerGroupbyTable
from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.tables as tables

#
# Description
#
description = """
<div style="width:500px">
<p>This example report demonstrates two different ways to utilize the
AnalysisTable features of App framework.

<p>The first table uses the extensible <strong>custom table definition</strong>
approach where two new classes are defined to perform the initial table
definition and data processing.

<p>The second table looks much like the first, but uses a <strong>single
function</strong> to perform the post-processing.

<p>Both approaches have benefits, the custom definitions allow far more
flexibility in how things get defined, while the function approach can
be simpler for a quick report.  See the <a href="edit/">report definition</a>
for details on how this was written.
</div>
"""

report = Report.create("Whois Example Report",
                       description=description, position=11)

report.add_section()

# Define a Table that gets external hosts by avg bytes
# This will be used as the base table for both analysis approaches
table = NetProfilerGroupbyTable.create(
    '5-hosts', groupby='host', duration='1 hour',
    filterexpr='not srv host 10/8 and not srv host 192.168/16'
)
table.add_column('host_ip', 'IP Addr', iskey=True, datatype='string')
table.add_column('avg_bytes', 'Avg Bytes', units='B/s', sortdesc=True)


# Using the custom analysis classes, this will create a new analysis table
# and also add the extra column of interest.
whoistable = WhoisTable.create('5-whois-hosts', tables={'t': table})

report.add_widget(tables.TableWidget, whoistable,
                  "Custom Analysis Link table", width=12)


# Create an Analysis table that calls the 'whois' function to create the link
# Note that we need to manually add the extra column here, since our
# function won't do that for us
function_table = AnalysisTable.create('whois-function-table',
                                      tables={'t': table},
                                      function=whois_function)
function_table.copy_columns(table)
function_table.add_column('whois', label='Whois link', datatype='html')

report.add_widget(tables.TableWidget, function_table,
                  "Analysis Function Link table", width=12)
