# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import functools

import logging
import datetime

import pytz
import numpy
import pandas
from rest_framework.reverse import reverse

from steelscript.appfwk.apps.alerting.models import Alert
from steelscript.appfwk.apps.datasource.forms import fields_add_time_selection
from steelscript.appfwk.apps.datasource.models import (DatasourceTable,
                                                       TableQueryBase, Column)
from steelscript.appfwk.apps.jobs import QueryComplete

logger = logging.getLogger(__name__)


class AlertTable(DatasourceTable):
    """ Query Alerts that have been stored in system. """
    class Meta:
        proxy = True

    _query_class = 'AlertQuery'

    TABLE_OPTIONS = {}
    FIELD_OPTIONS = {'duration': '1d',
                     'durations': ('1m', '15m', '1h', '4h', '1d',
                                   '1w', '4w', '12w', 'All')}

    def post_process_table(self, field_options):
        # Add criteria fields that are required by this table
        #

        # Add a time selection field
        fields_add_time_selection(self,
                                  initial_duration=field_options['duration'],
                                  durations=field_options['durations'],
                                  special_values=['All'])


class AlertQuery(TableQueryBase):
    """ Simple query to retrieve stored Alert objects. """

    def _get(self, alert, attr):
        """Returns attribute from alert or its associated Event.

        Raises AttributeError if attr not found in either object.
        """
        # Forces string-like objects to strings, since dicts get
        # passed in json and look like js objects when rendered by YUI

        for obj in (alert, alert.event):
            try:
                val = getattr(obj, attr.name)
                if attr.datatype in (Column.DATATYPE_STRING,
                                     Column.DATATYPE_HTML):
                    val = str(val)
                return val

            except AttributeError:
                continue
        raise AttributeError('%s not a valid attribute of Alert '
                             'or Event' % attr)

    def run(self):
        self.duration = self.job.criteria['duration']
        self.endtime = self.job.criteria['endtime']
        if self.duration == 'All':
            alerts = Alert.objects.all().order_by('timestamp')
            self.starttime = alerts[0].timestamp
        else:
            self.starttime = self.endtime - self.duration
            alerts = Alert.objects.filter(timestamp__range=(self.starttime,
                                                            self.endtime))

        columns = [col for col in self.table.get_columns(synthetic=False)]
        rows = [[self._get(a, c) for c in columns] for a in alerts]

        logger.debug('Alert query for duration %s returned %d rows' %
                     (self.duration, len(rows)))

        if rows:
            df = pandas.DataFrame(rows, columns=[c.name for c in columns])
        else:
            df = None

        self.data = df

        return self.post_run()

    def post_run(self):
        return QueryComplete(self.data)


class AlertHyperlinkedTable(AlertTable):
    """Return values grouped by given parameter."""
    class Meta:
        proxy = True
    _query_class = 'AlertHyperlinkedQuery'


class AlertHyperlinkedQuery(AlertQuery):
    def make_link(self, view_name, id_):
        link = reverse(view_name, args=[id_])
        s = ('<a href="%s" target="_blank">%s</a>' % (link, id_))
        return s

    def post_run(self):
        df = self.data
        if df is not None:
            if 'eventid' in df:
                make_link = functools.partial(self.make_link, 'event-lookup')
                df['eventid'] = df['eventid'].map(make_link)
            elif 'id' in df:
                make_link = functools.partial(self.make_link, 'alert-detail')
                df['id'] = df['id'].map(make_link)
            self.data = df
        return QueryComplete(self.data)


class AlertAnalysisGroupbyTable(AlertTable):
    """Return values grouped by given parameter."""
    class Meta:
        proxy = True
    _query_class = 'AlertAnalysisGroupbyQuery'


class AlertAnalysisGroupbyQuery(AlertQuery):

    def post_run(self):
        columns = self.table.column_set.order_by('id')
        groupby = columns[0].name

        if self.data is not None:
            dfg = self.data.groupby(groupby).count()
            self.data = dfg.reset_index()
        return QueryComplete(self.data)


class AlertAnalysisTimeseriesTable(AlertTable):
    """Return count of alerts aggregated by time interval."""
    class Meta:
        proxy = True
    _query_class = 'AlertAnalysisTimeseriesQuery'


class AlertAnalysisTimeseriesQuery(AlertQuery):

    def post_run(self):
        columns = self.table.column_set.order_by('id')
        timecol = columns[0].name
        datacol = columns[1].name

        if self.data is not None:
            dft = self.data.set_index(timecol)[datacol]
            # add null value to beginning and end of time series to make sure
            # resample interval lines up
            start = self.starttime.astimezone(pytz.UTC)
            end = self.endtime.astimezone(pytz.UTC)
            dft[start] = numpy.nan
            dft[end] = numpy.nan

            # adjust the resample size depending on overall time interval
            delta = end - start
            if delta <= datetime.timedelta(minutes=1):
                resample = '1S'
            elif delta <= datetime.timedelta(minutes=15):
                resample = '60S'  # 1 minute
            else:
                resample = '5T'   # 5 minutes

            dft = dft.resample(resample, how='count')
            self.data = dft.reset_index().rename(columns={'index': timecol})
        return QueryComplete(self.data)
