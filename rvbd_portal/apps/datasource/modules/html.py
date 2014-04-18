# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import logging

import pandas
from steelscript.common.jsondict import JsonDict
from rvbd_portal.apps.datasource.models import Column, Table, DatasourceTable

logger = logging.getLogger(__name__)


class HTMLTable(DatasourceTable):
    """ Takes arbitrary static html and wraps it in a simple table.

    When used with the 'raw.TableWidget' output, this can be rendered
    to the report page.
    """
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'html': None}

    def post_process_table(self, field_options):
        self.add_column(name='html', label='html')


class TableQuery(object):
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def __unicode__(self):
        return "<HTMLTable %s>" % self.job

    def __str__(self):
        return "<HTMLTable %s>" % self.job

    def mark_progress(self, progress):
        # Called by the analysis function
        self.job.mark_progress(70 + (progress * 30)/100)

    def run(self):
        # Collect all dependent tables
        options = self.table.options

        # create simple 1x1 table with html
        self.data = pandas.DataFrame([options.html], columns=['html'])

        logger.debug("%s: completed successfully" % self)
        return True
