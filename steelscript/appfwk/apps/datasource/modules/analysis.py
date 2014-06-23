# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging
from datetime import timedelta
import pandas

from steelscript.common.timeutils import \
    parse_timedelta, timedelta_total_seconds
from steelscript.appfwk.apps.datasource.models import \
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
    class Meta: proxy = True

    _ANALYSIS_TABLE_OPTIONS = {
        'tables': None,            # dependent tables to be run first
        'related_tables': None}    # related tables that are reference only

    _ANALYSIS_FIELD_OPTIONS = {
        'copy_fields': True }      # If true, copy TableFields from tables
                                   # and related_tables

    _query_class = 'AnalysisQuery'

    @classmethod
    def process_options(cls, table_options):
        # handle direct id's, table references, or table classes
        # from tables option and transform to simple table id value
        for i in ['tables', 'related_tables']:
            for k, v in (table_options[i] or {}).iteritems():
                table_options[i][k] = Table.to_ref(v)

        return table_options

    def post_process_table(self, field_options):
        if field_options['copy_fields']:
            keywords = set()
            for i in ['tables', 'related_tables']:
                refs = self.options[i] or {}
                for ref in refs.values():
                    table = Table.from_ref(ref)
                    for f in table.fields.all():
                        if f.keyword not in keywords:
                            self.fields.add(f)
                            keywords.add(f.keyword)


class AnalysisQuery(TableQueryBase):

    def run(self):
        # Collect all dependent tables
        deptables = self.table.options.tables
        if not deptables:
            self.tables = {}
            return True

        # Create dataframes for all dependent tables
        tables = {}

        logger.debug("%s: dependent tables: %s" % (self, deptables))
        depjobids = {}
        max_progress = (len(deptables)*100.0/float(len(deptables)+1))
        batch = BatchJobRunner(self.job, max_progress=max_progress)

        for (name, ref) in deptables.items():
            deptable = Table.from_ref(ref)
            job = Job.create(deptable, self.job.criteria)

            batch.add_job(job)
            logger.debug("%s: starting dependent job %s" % (self, job))
            depjobids[name] = job.id

        batch.run()

        logger.debug("%s: all dependent jobs complete, collecting data"
                     % str(self))

        failed = False
        for (name, id) in depjobids.items():
            job = Job.objects.get(id=id)

            if job.status == job.ERROR:
                self.job.mark_error("Dependent Job failed: %s" % job.message)
                failed = True
                break

            f = job.data()
            tables[name] = f
            logger.debug("%s: Table[%s] - %d rows" %
                         (self, name, len(f) if f is not None else 0))

        if failed:
            return False

        self.tables = tables

        logger.debug("%s: deptables completed successfully" % (self))
        return True


class CriteriaTable(AnalysisTable):
    class Meta: proxy = True

    _query_class = 'CriteriaQuery'

    def post_process_table(self, field_options):
        super(CriteriaTable, self).post_process_table(field_options)

        self.add_column('key', 'Criteria Key', iskey=True,
                        datatype=Column.DATATYPE_STRING)
        self.add_column('value', 'Criteria Value',
                        datatype=Column.DATATYPE_STRING)

class CriteriaQuery(AnalysisQuery):

    def post_run(self):
        criteria = self.job.criteria
        values = [[str(k),str(v)]
                  for k,v in criteria.iteritems()]
        values.append(['criteria.starttime', str(criteria.starttime)])
        df = pandas.DataFrame(values,
                              columns=['key', 'value']).sort('key')

        self.data = df
        return True

def resample(df, timecol, interval, how):
    """Resample the input dataframe.

    :param str timecol: the name of the column containing the row time
    :param timedelta,str interval: the new interval
    :param how: method for down or resampling (see pandas.Dataframe.resample)

    """
    df[timecol] = pandas.DatetimeIndex(df[timecol])
    df.set_index(timecol, inplace=True)
    if isinstance(interval, timedelta):
        interval = '%ss' % (timedelta_total_seconds(parse_timedelta(interval)))

    df = df.resample(interval, how=how).reset_index()
    return df
