# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import numpy
import pandas

from steelscript.appfwk.apps.alerting.models import Alert
from steelscript.appfwk.apps.datasource.forms import fields_add_time_selection
from steelscript.appfwk.apps.datasource.models import (DatasourceTable,
                                                       TableQueryBase)

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
        for obj in (alert, alert.event):
            try:
                return getattr(obj, attr)
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

        columns = [col.name for col in self.table.get_columns(synthetic=False)]
        rows = [[self._get(a, c) for c in columns] for a in alerts]

        logger.debug('Alert query for duration %s returned %d rows' %
                     (self.duration, len(rows)))

        if rows:
            df = pandas.DataFrame(rows, columns=columns)
        else:
            df = None

        self.data = df

        return True


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
            dfg.pop(groupby)
            self.data = dfg.reset_index()
        return True


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
            dft[self.starttime] = numpy.nan
            dft[self.endtime] = numpy.nan
            dft = dft.resample('5min', how='count')
            self.data = dft.reset_index().rename(columns={'index': timecol})
        return True
