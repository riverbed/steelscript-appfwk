# Copyright (c) 2018 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from steelscript.appfwk.apps.runbook.models import Workflow


def runbook_processor(request):

    workflows = Workflow.objects.all().order_by('title')

    if workflows:
        runbooks = []

        for w in workflows:
            runbooks.append((w.title, w.steps.all()))
    else:
        runbooks = []

    return {'runbooks': runbooks}
