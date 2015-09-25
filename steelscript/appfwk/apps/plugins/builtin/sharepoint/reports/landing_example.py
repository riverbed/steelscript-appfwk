# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.core.urlresolvers import reverse

from steelscript.appfwk.apps.datasource.modules.html import HTMLTable
from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.raw as raw
import steelscript.appfwk.apps.report.modules.maps as maps
import steelscript.appfwk.apps.report.modules.yui3 as yui3
from steelscript.netprofiler.appfwk.datasources.netprofiler import NetProfilerGroupbyTable
from steelscript.appfwk.apps.plugins.builtin.sharepoint.datasources.sharepoint import SharepointTable


logger = logging.getLogger(__name__)

#
# HTML Example Report
#

report = Report.create("Landing Page Example", position=9.1,
                       hide_criteria=True, reload_minutes=5)

report.add_section('Raw HTML')


# Define an image
imgurl = 'http://radar.weather.gov/Conus/Loop/NatLoop_Small.gif'
markup = '<img src="%s" alt="Doppler Radar National Mosaic Loop">' % imgurl

table = HTMLTable.create('Weather Image', html=markup)
report.add_widget(raw.TableWidget, table, 'weather image', width=6)


# Define an html table of links
# As an example of how the module loading works, this table
# may end up being shorter than the actual total number of reports
# because at the time this is calculated, all the remaining reports
# may not yet be in the database.
lines = []
reports = Report.objects.all().order_by('position')
for r in reports:
    kwargs = {'report_slug': r.slug,
              'namespace': r.namespace}

    url = reverse('report-view', kwargs=kwargs)
    line = '<li><a href="%s" target="_blank">%s</a></li>' % (url, r.title)
    lines.append(line)

markup = """
<ul>
%s
</ul>
""" % '\n'.join(lines)

table = HTMLTable.create('Report Links', html=markup)
report.add_widget(raw.TableWidget, table, 'report table', width=6)


# Define a map and table, group by location
p = NetProfilerGroupbyTable.create('maploc', groupby='host_group', duration=60,
                                resolution='auto')

p.add_column('group_name',    label='Group Name', iskey=True)
p.add_column('response_time', label='Resp Time',  units='ms')
p.add_column('network_rtt',   label='Net RTT',    units='ms')
p.add_column('server_delay',  label='Srv Delay',  units='ms')

report.add_widget(maps.MapWidget, p, "Response Time", width=5, height=300)


# Define a Sharepoint Table
s = SharepointTable.create('sp-documents',
                           site_url='/',
                           list_name='Shared Documents')

s.add_column('BaseName', sortasc=True)
s.add_column('Created', datatype='time')
s.add_column('Modified', datatype='time')
s.add_column('ID', datatype='string')
s.add_column('EncodedAbsUrl', datatype='string')

report.add_widget(yui3.TableWidget, s, "Sharepoint Documents List",
                  height=300, width=7)
