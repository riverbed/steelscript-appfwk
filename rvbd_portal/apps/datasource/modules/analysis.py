# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.

import logging
import pandas

from rvbd.common.jsondict import JsonDict
from rvbd_portal.apps.datasource.datasource import DatasourceTable
from rvbd_portal.apps.datasource.models import Column, Job, Table, BatchJobRunner

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

    `func` is a pointer to the user defined analysis function

    `params` is an optional dictionary of parameters to pass to `func`

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
                                 func = combine_by_host)
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
    EXTRA_TABLE_OPTIONS = {'tables': None,         # required, dict of tables
                           'related_tables': None, # additional tables
                           'func': None,           # required, function reference
                           'params': None}

    TABLE_FIELD_OPTIONS = {'copy_fields': True}

    def pre_process_table(self):
        # handle direct id's, table references, or table classes
        # from tables option and transform to simple table id value
        for k, v in self.extra_table_options['tables'].iteritems():
            if hasattr(v, 'table'):
                self.extra_table_options['tables'][k] = v.table.id
            else:
                self.extra_table_options['tables'][k] = getattr(v, 'id', v)

    def post_process_table(self):
        if self.table_field_options['copy_fields']:
            keywords = set()
            for name in ['tables', 'related_tables']:
                table_ids = self.extra_table_options[name]
                if not table_ids:
                    continue
                for table_id in table_ids.values():
                    for f in Table.objects.get(id=table_id).fields.all():
                        if f.keyword not in keywords:
                            self.table.fields.add(f)
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
            for (name, id) in deptables.items():
                id = int(id)
                deptable = Table.objects.get(id=id)
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
                     % (self, str(options.func)))

        try:
            df = options.func(self, dfs, self.job.criteria,
                              params=options.params)
        except AnalysisException as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.func, e.message))
            logger.exception("%s raised an exception" % self)
            return False
        except Exception as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.func, str(e)))
            logger.exception("%s: Analysis function %s raised an exception" %
                             (self, options.func))
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
                          columns=['key', 'value'])
    return df

def create_criteria_table(name):
    table = AnalysisTable.create('name', tables={},
                                 func = analysis_echo_criteria)

    Column.create(table, 'key', 'Criteria Key', iskey=True, isnumeric=False)
    Column.create(table, 'value', 'Criteria Value', isnumeric=False)
    return table
