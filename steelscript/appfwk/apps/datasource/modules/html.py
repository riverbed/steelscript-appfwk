# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas
from steelscript.appfwk.apps.datasource.models import \
    Column, Table, DatasourceTable, TableQueryBase

logger = logging.getLogger(__name__)


class HTMLTable(DatasourceTable):
    """ Takes arbitrary static html and wraps it in a simple table.

    When used with the 'raw.TableWidget' output, this can be rendered
    to the report page.
    """
    class Meta:
        proxy = True

    _query_class = 'HTMLQuery'

    TABLE_OPTIONS = {'html': None}

    def post_process_table(self, field_options):
        self.add_column(name='html', label='html')


class HTMLQuery(TableQueryBase):

    def run(self):
        # Collect all dependent tables
        options = self.table.options

        # create simple 1x1 table with html
        self.data = pandas.DataFrame([options.html], columns=['html'])

        logger.debug("%s: completed successfully" % self)
        return True
