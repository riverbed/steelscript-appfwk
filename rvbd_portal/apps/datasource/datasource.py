# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").
# This software is distributed "AS IS" as set forth in the License.
import copy
import logging
from django.utils.text import slugify

from rvbd.common.jsondict import JsonDict
from rvbd_portal.apps.datasource.models import Column, Table


logger = logging.getLogger(__name__)


class TableDatasourceOptions(JsonDict):
    pass


class ColumnDatasourceOptions(JsonDict):
    pass


class DatasourceTable(object):
    """ Provides base class for Datasources to inherit from.
    """
    table_params = {'filterexpr': None,
                    # less often used options
                    'rows': -1,
                    'cacheable': True,
                    'resample': False,
                    }
    table_options = {}

    field_params = {}

    column_params = {'label': None,
                     'position': None,
                     'iskey': False,
                     'isnumeric': True,
                     'datatype': '',
                     'units': '',
                     'issortcol': False,
                     # synthetic options
                     'synthetic': False,
                     'compute_post_resample': False,
                     'compute_expression': '',
                     'resample_operation': 'sum',
                     }
    column_options = {}

    def __init__(self, name, **kwargs):
        """ Initialize object. """
        self.slug = '%s_%s' % (self.__class__.__name__, slugify(unicode(name)))
        self.name = name
        self.table = None
        self.columns = []

        # handle custom defaults
        self.set_defaults()

        self.validate_args(**kwargs)
        self.create_table()
        self.post_process_table()           # add custom fields, etc

    def set_defaults(self):
        """ Method to add/override defaults without redefining the
        whole class dict.
        """
        pass

    def validate_args(self, **kwargs):
        """ Process keyword arguments and raise error if invalid items found.
        """
        keys = kwargs.keys()
        tp = dict((k, kwargs.pop(k)) for k in keys if k in self.table_params)
        self.table_params.update(**tp)

        to = dict((k, kwargs.pop(k)) for k in keys if k in self.table_options)
        self.table_options.update(**to)

        fp = dict((k, kwargs.pop(k)) for k in keys if k in self.field_params)
        self.field_params.update(**fp)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

    def create_table(self):
        """ Create a datasource table. """

        logger.debug('Creating table %s' % self.slug)

        if self.table_options:
            options = TableDatasourceOptions(default=self.table_options,
                                             **self.table_options)
        else:
            options = None

        self.table = Table.create(name=self.slug, module=self.__module__,
                                  options=options,
                                  **self.table_params)

    def post_process_table(self):
        """ Hook to add custom fields, or other post-table creation operations.
        """
        pass

    def add_column(self, name, label=None, **kwargs):
        """ Create a column object. """
        column_params = copy.deepcopy(self.column_params)
        column_options = copy.deepcopy(self.column_options)

        keys = kwargs.keys()
        cp = dict((k, kwargs.pop(k)) for k in keys if k in column_params)
        column_params.update(**cp)

        co = dict((k, kwargs.pop(k)) for k in keys if k in column_options)
        column_options.update(**co)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

        if self.column_options:
            options = ColumnDatasourceOptions(default=column_options,
                                              **column_options)
        else:
            options = None

        c = Column.create(self.table, name, options=options,
                          **column_params)
        return c
