# Copyright (c) 2016 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse

from steelscript.appfwk.apps.datasource.models import \
    Column, DatasourceTable, TableQueryBase
from steelscript.appfwk.apps.jobs import QueryError, QueryComplete
from steelscript.appfwk.apps.metrics.models import get_schema_map

logger = logging.getLogger(__name__)


class MetricsTable(DatasourceTable):
    """Query internal metrics app for tabular results.
    """
    class Meta:
        proxy = True

    _query_class = 'MetricsQuery'

    TABLE_OPTIONS = {'schema': None}

    def post_process_table(self, field_options):
        if self.options.schema is None:
            raise AttributeError('Table %s missing option "schema" which '
                                 'must be specified when creating a '
                                 'MetricsTable.' % self.name)


class MetricsQuery(TableQueryBase):

    def run(self):
        # Collect all dependent tables
        options = self.table.options

        model = get_schema_map()[options.schema]
        df = model.objects.get_dataframe()

        if df.empty:
            return QueryError(
                'No metrics defined for schema "%s".  Add new metrics '
                'using the <a href="%s">admin interface</a>.'
                % (options.schema,
                   reverse('admin:metrics_plugin_%s_changelist'
                           % model.__name__.lower()))
            )

        # Add some default columns as needed
        # new ones are created as normal columns vs ephemeral - the table
        # schema will not be dynamic, any changes will be done via code
        # changes and/or a report reload.

        # We check to see if some have already been defined to allow for
        # customization of the actual labels or column display
        keys = list(df.keys())

        for k in keys:
            try:
                Column.objects.get(table=self.job.table, name=k)
            except ObjectDoesNotExist:
                Column.create(self.job.table, k, k.title(), datatype='string')

        logger.debug("%s: completed successfully" % self)
        return QueryComplete(df)
