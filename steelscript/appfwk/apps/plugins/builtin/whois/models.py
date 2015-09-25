# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.plugins import Plugin, register


class WhoisReport(Plugin):
    title = 'Whois Report Plugin'
    description = 'Example Plugin providing report and helper script'
    version = '0.1'
    author = 'Riverbed Technology'

    enabled = True
    can_disable = True

    reports = ['reports']
    libraries = ['libs']


register(WhoisReport)
