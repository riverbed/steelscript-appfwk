# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas

from steelscript.appfwk.apps.datasource.models import\
     DatasourceTable, Column, Job, Table, TableQueryBase, BatchJobRunner
from steelscript.appfwk.libs.fields import Function


logger = logging.getLogger(__name__)


class AnalysisException(Exception):
    def _init__(self, message, *args, **kwargs):
        self.message = message
        super(AnalysisException, self).__init__(*args, **kwargs)


class AnalysisTable(DatasourceTable):
    """
    An AnalysisTable builds on other tables, running them first to collect
    data, then extracting the data as pandas.DataFrame objects.  The
    set of DataFrames is then passed to a user defined function that
    must return a DataFrame with columns matching the Columns associated
    with this Table.

    `tables` is hashmap of dependent tables, mapping a names expected
        by the analysis functon to table ids

    `function` is a pointer to the user defined analysis function, or
        a Function object which includes parameters

    For example, consider an input of two tables A and B, and an
    AnalysisTable that simply concatenates A and B:

        A = Table.create('A')
        Column.create(A, 'host')
        Column.create(A, 'bytes')

        B = Table.create('B')
        Column.create(B, 'host')
        Column.create(B, 'pkts')

        from config.reports.helpers.analysis_funcs import combine_by_host

        Combined = AnalysisTable('Combined',
                                 tables = {'t1': A,
                                           't2': B},
                                 function = combine_by_host)
        Combined.add_column('host')
        Combined.add_column('bytes')
        Combined.add_column('pkts')

    Then in config/reports/helpers/analysis_func.py

        def combine_by_host(dst, srcs):
            # Get the pandas.DataFrame objects for t1 and t2
            t1 = srcs['t1']
            t2 = srcs['t2']

            # Now create a new DataFrame that joins these
            # two tables by the 'host'
            df = pandas.merge(t1, t2, left_on='host', right_on='host',
                              how='outer')
            return df

    Note that the function must defined in a separate file in the 'helpers'
    directory.
    """
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'function': None}         # Function object

    @classmethod
    def process_options(cls, table_options):
        if not isinstance(table_options['function'], Function):
            table_options['function'] = Function(table_options['function'])

        return table_options


class TableQuery(TableQueryBase):

    def run(self):
        tables = self.tables or {}
        reltables = self.table.related_tables or {}
        for table_name in reltables:
            tables[table_name] = Table.from_ref(reltables[table_name])

        options = self.table.options
        try:
            df = options.function(self, tables, self.job.criteria)
        except AnalysisException as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.function, e.message))
            logger.exception("%s raised an exception" % self)
            return False
        except Exception as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.function, str(e)))
            logger.exception("%s: Analysis function %s raised an exception" %
                             (self, options.function))
            return False

        self.data = df

        logger.debug("%s: completed successfully" % (self))
        return True

def analysis_echo_criteria(query, tables, criteria, params):
    values = [[str(k),str(v)]
              for k,v in criteria.iteritems()]
    values.append(['criteria.starttime', str(criteria.starttime)])
    df = pandas.DataFrame(values,
                          columns=['key', 'value']).sort('key')

    return df

def create_criteria_table(name):
    table = AnalysisTable.create(name, tables={},
                                 function = analysis_echo_criteria)

    Column.create(table, 'key', 'Criteria Key', iskey=True,
                  datatype=Column.DATATYPE_STRING)
    Column.create(table, 'value', 'Criteria Value',
                  datatype=Column.DATATYPE_STRING)
    return table
