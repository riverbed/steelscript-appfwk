# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from itertools import groupby

from steelscript.appfwk.apps.report.models import Report


def report_list_processor(request):
    reports = []
    r = Report.objects.filter(enabled=True).order_by('namespace',
                                                     'position',
                                                     'title')
    for k, g in groupby(r, lambda x: x.namespace):
        # because of ordering above, the 'default' namespace items
        # will always appear first before any 'default' reports
        if k in ('default', 'custom', 'appfwk'):
            reports[0:0] = list(g)
        else:
            reports.append((k, list(g)))

    return {'reports': reports}
