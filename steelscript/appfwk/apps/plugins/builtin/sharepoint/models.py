# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.plugins import Plugin, register

note = ''
try:
    import sharepoint
    import ntlm
    import lxml
except ImportError:
    note = """
<br><b>IMPORTANT NOTE</b>: additional python packages need to be installed
in order to use this Plugin:<br>
<blockquote>
sharepoint>=0.3.2,<=0.4<br>
python-ntlm==1.0.1<br>
</blockquote>
"""


class SharepointPlugin(Plugin):
    title = 'Sharepoint Datasource Plugin'
    description = ('A Portal datasource plugin to interact with Sharepoint '
                   'devices and services.<br>' + note)
    version = '0.1.1'
    author = 'Riverbed Technology'

    enabled = False
    can_disable = True

    devices = ['devices']
    datasources = ['datasources']
    reports = ['reports']

register(SharepointPlugin)
