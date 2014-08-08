# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

import pandas

from steelscript.appfwk.apps.alerting.models import Alert
from steelscript.appfwk.apps.datasource.models import DatasourceTable, TableQueryBase
from steelscript.appfwk.apps.datasource.forms import fields_add_time_selection

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

    def run(self):
        duration = self.job.criteria['duration']
        print duration
        if duration == 'All':
            alerts = Alert.objects.all().order_by('timestamp')
        else:
            endtime = self.job.criteria['endtime']
            starttime = endtime - duration
            alerts = Alert.objects.filter(timestamp__range=(starttime, endtime))

        columns = [col.name for col in self.table.get_columns(synthetic=False)]
        rows = [[getattr(a, c) for c in columns] for a in alerts]

        logger.debug('Alert query for duration %s returned %d rows' %
                     (duration, len(rows)))

        if rows:
            df = pandas.DataFrame(rows, columns=columns)
        else:
            df = []

        self.data = df

        return True
