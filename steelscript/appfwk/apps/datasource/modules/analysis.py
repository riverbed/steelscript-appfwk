# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas

from steelscript.appfwk.apps.datasource.models import (DatasourceTable, Column, Job,
                                                Table,  BatchJobRunner)
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

    TABLE_OPTIONS = {'tables': None,           # required, dict of table ids
                     'related_tables': None,   # additional table ids
                     'function': None}         # Function object

    FIELD_OPTIONS = {'copy_fields': True}

    @classmethod
    def process_options(cls, table_options):
        # handle direct id's, table references, or table classes
        # from tables option and transform to simple table id value
        for name in ['tables', 'related_tables']:
            for k, v in (table_options[name] or {}).iteritems():
                table_options[name][k] = Table.to_ref(v)

        if not isinstance(table_options['function'], Function):
            table_options['function'] = Function(table_options['function'])

        return table_options

    def post_process_table(self, field_options):
        if field_options['copy_fields']:
            keywords = set()
            for name in ['tables', 'related_tables']:
                refs = self.options[name] or {}
                for ref in refs.values():
                    table = Table.from_ref(ref)
                    for f in table.fields.all():
                        if f.keyword not in keywords:
                            self.fields.add(f)
                            keywords.add(f.keyword)


class TableQuery(object):
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def __unicode__(self):
        return "<AnalysisTable %s>" % self.job

    def __str__(self):
        return "<AnalysisTable %s>" % self.job

    def mark_progress(self, progress):
        # Called by the analysis function
        self.job.mark_progress(70 + (progress * 30)/100)

    def run(self):
        # Collect all dependent tables
        options = self.table.options

        # Create dataframes for all tables
        dfs = {}

        deptables = options.tables
        if deptables and (len(deptables) > 0):
            logger.debug("%s: dependent tables: %s" % (self, deptables))
            depjobids = {}
            batch = BatchJobRunner(self.job, max_progress=70)
            for (name, ref) in deptables.items():
                deptable = Table.from_ref(ref)
                job = Job.create(
                    table=deptable,
                    criteria=self.job.criteria.build_for_table(deptable)
                )
                batch.add_job(job)
                logger.debug("%s: starting dependent job %s" % (self, job))
                depjobids[name] = job.id

            batch.run()

            logger.debug("%s: All dependent jobs complete, collecting data"
                         % str(self))

            failed = False
            for (name, id) in depjobids.items():
                job = Job.objects.get(id=id)

                if job.status == job.ERROR:
                    self.job.mark_error("Dependent Job failed: %s" % job.message)
                    failed = True
                    break

                f = job.data()
                dfs[name] = f
                logger.debug("%s: Table[%s] - %d rows" %
                             (self, name, len(f) if f is not None else 0))

            if failed:
                return False

        logger.debug("%s: Calling analysis function %s"
                     % (self, options.function))

        try:
            df = options.function(self, dfs, self.job.criteria)
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

        # Sort according to the defined sort columns
        if df is not None:
            if self.table.sortcol:
                n = self.table.sortcol.name
                sorted = df.sort(n, ascending=False)
                # Move NaN rows to the end
                df = (sorted[sorted[n].notnull()]
                      .append(sorted[sorted[n].isnull()]))

            if self.table.rows > 0:
                self.data = df[:self.table.rows]
            else:
                self.data = df
        else:
            self.data = None

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
    table = AnalysisTable.create('name', tables={},
                                 function = analysis_echo_criteria)

    Column.create(table, 'key', 'Criteria Key', iskey=True,
                  datatype=Column.DATATYPE_STRING)
    Column.create(table, 'value', 'Criteria Value',
                  datatype=Column.DATATYPE_STRING)
    return table
