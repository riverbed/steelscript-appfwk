# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report, Section
import steelscript.appfwk.apps.report.modules.yui3 as yui3

from steelscript.appfwk.apps.plugins.builtin.sharepoint.datasources.sharepoint import SharepointTable

#
# SharePoint report
#

report = Report(title="Sharepoint", position=11)
report.save()

section = Section.create(report)


# Define a Sharepoint Table
s = SharepointTable.create('Shared Documents',
                           site_url='/',
                           list_name='Shared Documents')

s.add_column('BaseName', sortasc=True, datatype='string')
s.add_column('Created', datatype='time')
s.add_column('Modified', datatype='time')
s.add_column('ID', datatype='string')
s.add_column('EncodedAbsUrl', datatype='string')

yui3.TableWidget.create(section, s, "Sharepoint Documents List",
                        height=300, width=12)
