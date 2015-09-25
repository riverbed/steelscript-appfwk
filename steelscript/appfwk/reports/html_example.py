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


logger = logging.getLogger(__name__)

#
# HTML Example Report
#

report = Report.create("HTML Example", position=11)

report.add_section('Raw HTML')


# Define an image
imgurl = 'http://radar.weather.gov/Conus/Loop/NatLoop_Small.gif'
markup = '<img src="%s" alt="Doppler Radar National Mosaic Loop">' % imgurl

table = HTMLTable.create('Weather Image', html=markup)
report.add_widget(raw.TableWidget, table, 'weather image')


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
report.add_widget(raw.TableWidget, table, 'report table')
