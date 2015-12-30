# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from steelscript.appfwk.apps.datasource.models import \
    DatasourceTable, TableQueryBase
from steelscript.appfwk.apps.jobs import Job, QueryComplete, QueryContinue

logger = logging.getLogger(__name__)


class ReportStatus(object):
    NEW = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3


class ReportStatusTable(DatasourceTable):
    """ Table that takes the id of report history and returns its status."""
    class Meta:
        proxy = True

    _query_class = 'ReportStatusQuery'

    TABLE_OPTIONS = {}


class ReportStatusQuery(TableQueryBase):

    def run(self):
        """ Update the status of the report history. If one widget job's status
        is ERROR, then update the status of the report history as ERROR; if one
        report job's status is running, then update the status of the report
        history as RUNNING; if all jobs' status are COMPLETE, then update the
        status of the report history as COMPLETE.
        """
        record = self.job.criteria.report_history

        jobs = Job.objects.filter(handle__in=record.job_handles.split(','))

        if any([job.status == Job.ERROR for job in jobs]):
            record.update_status(ReportStatus.ERROR)
            return QueryComplete(None)

        elif any([job.status == Job.RUNNING for job in jobs]):
            record.update_status(ReportStatus.RUNNING)
            return QueryContinue(self.run)

        elif jobs and all([job.status == Job.COMPLETE for job in jobs]):
            record.update_status(ReportStatus.COMPLETE)
            return QueryComplete(None)

        return QueryContinue(self.run)
