# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import copy
import pandas
import logging
import hashlib

from functools import partial

from steelscript.appfwk.apps.jobs.models import Job
from steelscript.appfwk.apps.datasource.models import Table
from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable,\
    AnalysisQuery
from steelscript.appfwk.apps.jobs import QueryComplete, QueryContinue
from steelscript.appfwk.apps.db import storage, ColumnFilter, \
    ExistingIntervals
from steelscript.common.interval import Interval, IntervalList
from steelscript.appfwk.apps.datasource.models import Column
from steelscript.common.timeutils import round_time, timedelta_total_seconds,\
    force_to_utc, TimeParser

logger = logging.getLogger(__name__)

TIME_FIELDS = ['_orig_duration', '_orig_endtime', '_orig_starttime',
               'duration', 'endtime', 'starttime']


def make_index(s):
    return 'appfwk-{0}'.format(s)


class TimeInterval(Interval):
    def __init__(self, start, end):
        self.start = force_to_utc(start)
        self.end = force_to_utc(end)

    def localize_tz(self, tzinfo):
        self.start = self.start.astimezone(tzinfo)
        self.end = self.end.astimezone(tzinfo)


class TimeSeriesTable(AnalysisTable):

    class Meta:
        proxy = True

    _query_class = 'TimeSeriesQuery'

    TABLE_OPTIONS = {'max_length_per_call': 3600,
                     'max_number_of_calls': 2,
                     'id_method': 'time',
                     'override_table_handle': None,
                     'table_filter': None,
                     'override_index': None,
                     }


class TimeSeriesQuery(AnalysisQuery):

    def __init__(self, *args, **kwargs):
        super(AnalysisQuery, self).__init__(*args, **kwargs)

        self.ds_table = Table.from_ref(self.table.options.related_tables['ds'])

        self.time_col = [col.name for col in self.ds_table.get_columns()
                         if col.datatype == Column.DATATYPE_TIME][0]

        starttime, endtime, self.resolution = self._round_times()
        self.query_interval = TimeInterval(starttime, endtime)

        self.handle, self.no_time_criteria = self._calc_handle()

        logger.debug('TimeSeriesQuery initialized - job: %s, table: %s, '
                     'interval: %s, handle: %s' %
                     (self.job, self.table, self.query_interval, self.handle))

    def _calc_handle(self):
        """ Compute the handle corresponding to the table object
        and the criteria fields, excluding fields such as 'endtime',
        'starttime' and 'duration'.

        If the handle was specified via override in table options,
        we use that value instead.  This allows for tables from separate
        reports to store/retrieve the same data set.

        :return: the hash hex string and the criteria without time values
        """
        criteria = copy.copy(self.job.criteria)

        for k, v in self.job.criteria.iteritems():
            if k in TIME_FIELDS:
                # We do not want time related fields included in the criteria
                criteria.pop(k, None)
                continue

        if self.table.options.override_table_handle:
            handle = self.table.options.override_table_handle
        else:
            h = hashlib.md5()
            h.update(str(self.table.id))

            h.update('.'.join([c.name for c in self.ds_table.get_columns()]))

            for k, v in self.job.criteria.iteritems():
                h.update('%s:%s' % (k, v))

            handle = h.hexdigest()

        return handle, criteria

    def _check_intervals(self, intervals):

        max_len = self.table.options.max_length_per_call * self.resolution
        max_calls = self.table.options.max_number_of_calls

        ret = IntervalList([])

        err_msg = ("Could not fulfill the query for %s. "
                   "Max length for each query is %s. "
                   "Max number of queries is %s. "
                   % (intervals, max_len, max_calls))

        calls_left = max_calls

        for interval in intervals:
            if calls_left <= 0 or \
                    interval.size > max_len * calls_left:
                raise ValueError(err_msg)
            if interval.size <= max_len:
                ret.append(interval)
                calls_left -= 1
            else:  # interval.size <= max_len * calls_left:
                while interval.size > max_len:
                    one_int = TimeInterval(interval.start,
                                           interval.start + max_len)
                    interval = (interval - one_int)[0]
                    calls_left -= 1
                    ret.append(one_int)

                # Add the remaining interval
                ret.append(interval)
                calls_left -= 1

        return ret

    def _round_times(self):
        """Round the start/end time in criteria to reflect what data will be
        returned from data source and saved in db (based on investigation of
        NetProfiler/NetShark query results).

        Start/End time needs to round down to closest time in integer
        resolutions. However, if either starttime or endtime in criteria is
        already in integer resolutions, it should remain the same.

        :return: start time, end time, resolution
        """

        self.job.criteria.compute_times()

        resolution = getattr(self.job.criteria, 'resolution', None)
        if not resolution:
            raise AttributeError("The data source table '%s' needs to have "
                                 "'resolution' field." % self.ds_table.name)

        resolution_sec = timedelta_total_seconds(self.job.criteria.resolution)

        starttime = round_time(self.job.criteria.starttime,
                               round_to=resolution_sec,
                               trim=True)

        endtime = round_time(self.job.criteria.endtime,
                             round_to=resolution_sec,
                             trim=True)

        return starttime, endtime, resolution

    def query(self, starttime, endtime):
        logger.debug('Querying database for range: %s to %s' %
                     (starttime, endtime))

        col_filters = [ColumnFilter(
                       query_type='range',
                       query={self.time_col: {'gte': starttime,
                                              'lte': endtime}
                              })]

        if self.table.options.table_filter:
            # (type, col, value)
            type_, colname, value = self.table.options.table_filter.split(':')
            tbl_filter = ColumnFilter(
                query_type=type_,
                query={colname: value}
            )
            col_filters.append(tbl_filter)
            logger.debug('Added extra table filter: {}'.format(col_filters))

        # Obtain result from storage as a list of dicts,
        # each dict represents one record/doc
        if self.table.options.override_index:
            index = self.table.options.override_index
        else:
            index = make_index(self.ds_table.namespace)

        res = storage.search(index=index,
                             doc_type=self.handle,
                             col_filters=col_filters)

        # The time field is a string formatted as "YYYY/MM/DDTHH:MM:SS"
        # Need to convert it to datetime type
        if not res:
            return None

        make_ts = partial(pandas.Timestamp, tz='UTC')
        df = pandas.DataFrame(res)
        df[self.time_col] = df[self.time_col].map(make_ts)

        return df.sort(self.time_col)

    def _converge_adjacent(self, intervals):

        itvs = []
        current_interval = None
        for interval in intervals:
            if current_interval is None:
                current_interval = interval
            elif current_interval.end + self.resolution == interval.start:
                current_interval = TimeInterval(current_interval.start,
                                                interval.end)
            else:
                itvs.append(current_interval)
                current_interval = interval
        itvs.append(current_interval)
        interval_list = IntervalList(itvs)

        logger.debug('Merging intervals from %s --> %s' % (intervals, itvs))
        return interval_list

    def analyze(self, jobs=None):
        logger.debug('TimeSeriesTable analysis with jobs %s' % jobs)

        filtered_list = ExistingIntervals.objects.filter(
            table_handle=self.handle,
            criteria=self.no_time_criteria
        )

        existing_intervals = None

        if filtered_list:
            existing_intervals = filtered_list[0].intervals
            logger.debug('Found existing intervals for handle %s: %s' %
                         (self.handle, existing_intervals))

            if self.query_interval in existing_intervals:
                logger.debug('Query interval totally covered by DB, returning '
                             'DB query.')
                # Search DB for the queried data
                data = self.query(self.query_interval.start,
                                  self.query_interval.end)
                return QueryComplete(data)

            logger.debug('Query interval only partially covered by DB ...')

        intervals_to_call = self._check_intervals(
            self.query_interval - existing_intervals)

        logger.debug('Setting up %d jobs to cover missing data '
                     'for these intervals: %s' % (len(intervals_to_call),
                                                  intervals_to_call))
        dep_jobs = {}
        for interval in intervals_to_call:
            criteria = copy.copy(self.job.criteria)
            # Use the two time related fields
            criteria.starttime = interval.start
            criteria.endtime = interval.end
            job = Job.create(table=self.ds_table, criteria=criteria,
                             update_progress=False, parent=self.job)
            dep_jobs[job.id] = job

        return QueryContinue(self.collect, jobs=dep_jobs)

    def collect(self, jobs=None):
        logger.debug('TimeSeriesTable collect with jobs %s' % jobs)
        dfs_from_jobs, dfs_from_db = [], []

        objs = ExistingIntervals.objects.filter(table_handle=self.handle,
                                                criteria=self.no_time_criteria)

        if objs:
            # we should only find one with our handle
            if len(objs) > 1:
                logger.warning('Multiple instances of ExistingIntervals found '
                               'for handle %s, taking first one.'
                               % self.handle)
            obj = objs[0]

            # Query for the intervals already in db
            itvs_in_db = self.query_interval.intersection(obj.intervals)
            dfs_from_db = [self.query(itv.start, itv.end)
                           for itv in itvs_in_db]
        else:
            logger.debug('Creating new ExistingIntervals object for '
                         'namespace: %s, sourcefile: %s, table: %s, handle: %s'
                         % (self.ds_table.namespace, self.ds_table.sourcefile,
                            self.ds_table.name, self.handle))

            obj = ExistingIntervals(namespace=self.ds_table.namespace,
                                    sourcefile=self.ds_table.sourcefile,
                                    table=self.ds_table.name,
                                    criteria=self.no_time_criteria,
                                    table_handle=self.handle,
                                    intervals=IntervalList([]))

        job_intervals = obj.intervals

        for job_id, job in jobs.iteritems():
            df = job.data()
            if df is None:
                continue
            dfs_from_jobs.append(df)

            # evaluate job time interval extents

            # Handle case where data returned slightly smaller than base query.
            # This can be caused because data doesn't always align with query
            # edges, but as a result any future queries of the same requested
            # time interval would return the same results.

            # if our new interval is entirely within the original query,
            # and the deltas at each of the edges is less than the resolution
            # of the table, then we got the best we could hope for,
            # and we should just add the interval as originally requested.
            job_criteria_start = job.criteria.starttime
            job_criteria_end = job.criteria.endtime

            job_data_start = df[self.time_col].min().to_datetime()
            job_data_end = df[self.time_col].max().to_datetime()

            if abs(job_data_start - job_criteria_start) < self.resolution:
                interval_start = job_criteria_start
            else:
                interval_start = job_data_start

            if abs(job_criteria_end - job_data_end) < self.resolution:
                interval_end = job_criteria_end
            else:
                interval_end = job_data_end

            logger.debug('Job time intervals: Criteria - (%s, %s), '
                         'Data - (%s, %s)' %
                         (job_criteria_start, job_criteria_end,
                          job_data_start, job_data_end))

            interval = TimeInterval(interval_start, interval_end)
            logger.debug('Appending TimeInterval: %s' % interval)

            job_intervals += interval

        if not dfs_from_jobs:
            return QueryComplete(None)

        if self.table.options.override_index:
            index = self.table.options.override_index
        else:
            index = make_index(self.ds_table.namespace)

        storage.write(index=index,
                      doctype=self.handle,
                      data_frame=pandas.concat(dfs_from_jobs,
                                               ignore_index=True),
                      timecol=self.time_col,
                      id_method=self.table.options.id_method)

        obj.intervals = self._converge_adjacent(job_intervals)
        obj.tzinfo = self.job.criteria.starttime.tzinfo

        # Only update existing intervals if writing to db succeeds
        obj.save()

        # Immediately reading from db after writing results can result in
        # non-correct data, thus stitching the data frames together
        total_df = pandas.concat(dfs_from_db + dfs_from_jobs,
                                 ignore_index=True)
        data = total_df.sort(self.time_col).drop_duplicates()

        return QueryComplete(data)
