# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.report.models import Report


def report_list_processor(request):
    return {'reports': (Report.objects.filter(enabled=True)
                        .order_by('position', 'title'))}
