# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import time
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

    `function` is a pointer to the user defined analysis function

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
                                 tables={'t1': A,
                                         't2': B},
                                 function=combine_by_host)
        Combined.add_column('host')
        Combined.add_column('bytes')
        Combined.add_column('pkts')

    Then in config/reports/helpers/analysis_func.py

        def combine_by_host(query, tables, criteria, params):
            # Get the pandas.DataFrame objects for t1 and t2
            t1 = tables['t1']
            t2 = tables['t2']

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

    _ANALYSIS_TABLE_OPTIONS = {
        'tables': None,            # dependent tables to be run first
        'related_tables': None,    # related tables that are reference only
        'function': None           # optional function for post process
    }

    _ANALYSIS_FIELD_OPTIONS = {
        'copy_fields': True      # If true, copy TableFields from tables
    }                            # and related_tables

    _query_class = 'AnalysisQuery'

    @classmethod
    def process_options(cls, table_options):
        # handle direct id's, table references, or table classes
        # from tables option and transform to simple table id value
        for i in ['tables', 'related_tables']:
            for k, v in (table_options[i] or {}).iteritems():
                table_options[i][k] = Table.to_ref(v)

        tf = table_options['function']
        if tf and not isinstance(tf, Function):
            table_options['function'] = Function(tf)

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
                self.job.mark_error("Dependent Job failed: %s" % job.message,
                                    exception=job.exception)
                failed = True
                break

            f = job.data()
            tables[name] = f
            logger.debug("%s: Table[%s] - %d rows" %
                         (self, name, len(f) if f is not None else 0))

        if failed:
            return False

        self.tables = tables

        logger.debug("%s: deptables completed successfully" % self)
        return True

    def post_run(self):
        """Execute any Functions saved to Table.

        In most cases, this function will be simply overridden by a
        subclass which will implement its own detailed processing.  This
        method provides a shortcut to support passing a Function
        directly to the create method.
        """
        options = self.table.options

        try:
            df = options.function(self, options.tables, self.job.criteria)

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

        logger.debug("%s: completed successfully" % self)
        return True


class FocusedAnalysisTable(AnalysisTable):
    """
    Finds the max/min of a source table, and runs a new table focused
    around that time period.

    Takes two source tables, 'template' and 'source'.  An example definition:

    a = FocusedAnalysisTable.create(name='zoomed table',
                                    max=True,
                                    zoom_duration='1s',
                                    zoom_resolution='1ms',
                                    tables={'source': table1},
                                    related_tables={'template': table2})

    The template table defines the datasource and associated columns, no
    columns should be added to a FocusedAnalysisTable.

    This requires a time-series based 'source' table, but the secondary
    'template' table to run can be any type of datasource table.  For instance,
    a 24-hour NetProfiler table can be used as the source, and with a NetShark
    template table, the peaks or valleys can be shown in a separate widget
    using more granular timeframe and resolution.
    """
    class Meta:
        proxy = True

    _query_class = 'FocusedAnalysisQuery'

    TABLE_OPTIONS = {'max': True,
                     'zoom_duration': '1s',
                     'zoom_resolution': '1ms',
                     }

    def post_process_table(self, field_options):
        super(FocusedAnalysisTable, self).post_process_table(field_options)

        # take template table and copy its columns
        ref = self.options['related_tables']['template']
        self.copy_columns(ref)


class FocusedAnalysisQuery(AnalysisQuery):
    def post_run(self):
        basetable = Table.from_ref(
            self.table.options['related_tables']['template']
        )
        data = self.tables['source']

        # find column whose min/max is largest deviation from mean
        # then take row from that column where min/max occurs
        if self.table.options['max']:
            idx = (data.max() / data.mean()).idxmax()
            frow = data.ix[data[idx].idxmax()]
        else:
            idx = (data.min() / data.mean()).idxmin()
            frow = data.ix[data[idx].idxmin()]

        # get time value from extracted row to calculate new start/end times
        ftime = frow['time']
        duration = parse_timedelta(self.table.options['zoom_duration'])
        resolution = parse_timedelta(self.table.options['zoom_resolution'])
        stime = ftime - (duration / 2)
        etime = ftime + (duration / 2)

        criteria = self.job.criteria
        criteria['resolution'] = resolution
        criteria['duration'] = duration
        criteria['_orig_duration'] = duration
        criteria['starttime'] = stime
        criteria['_orig_starttime'] = stime
        criteria['endtime'] = etime
        criteria['_orig_endtime'] = etime

        logging.debug('Creating FocusedAnalysis job with updated criteria %s'
                      % criteria)

        job = Job.create(basetable, criteria)
        job.start()

        while job.status == Job.RUNNING:
            time.sleep(1)

        if job.status == job.ERROR:
            self.job.mark_error("Dependent Job failed: %s" % job.message,
                                exception=job.exception)
            return False

        self.data = job.data()

        return True


class CriteriaTable(AnalysisTable):
    class Meta:
        proxy = True

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
