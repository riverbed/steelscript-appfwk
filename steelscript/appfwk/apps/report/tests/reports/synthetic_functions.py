import logging

import pandas
from steelscript.common.timeutils import datetime_to_seconds
from steelscript.appfwk.apps.datasource.modules.analysis \
    import AnalysisTable, AnalysisQuery
from steelscript.appfwk.apps.datasource.forms \
    import fields_add_time_selection, fields_add_resolution

logger = logging.getLogger(__name__)


class SyntheticGenerateTable(AnalysisTable):
    class Meta:
        proxy = True

    TABLE_OPTIONS = {'source_resolution': 1}

    _query_class = 'SyntheticGenerateQuery'

    def post_process_table(self, field_options):
        self.add_column('time', 'Time', iskey=True, datatype='time')
        self.add_column('value', 'Value')
        fields_add_time_selection(self)
        fields_add_resolution(self)


class SyntheticGenerateQuery(AnalysisQuery):

    def post_run(self):
        t0 = datetime_to_seconds(self.job.criteria.starttime)
        t1 = datetime_to_seconds(self.job.criteria.endtime)

        data = []
        for t in range(t0, t1, self.table.options['source_resolution']):
            data.append([t, 1])

        df = pandas.DataFrame(data, columns=['time', 'value'])
        df['time'] = df['time'].astype('datetime64[s]')

        self.data = df
        return True
