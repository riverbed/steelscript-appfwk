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
    TABLE_OPTIONS = {'filterexpr': None,
                     # less often used options
                     'rows': -1,
                     'cacheable': True,
                     'resample': False,
                     }
    EXTRA_TABLE_OPTIONS = {}                      # can override in subclass

    TABLE_FIELD_OPTIONS = {}                       # can override in subclass

    COLUMN_OPTIONS = {'label': None,
                      'position': None,
                      'iskey': False,
                      'datatype': 'float',
                      'units': 'none',
                      'issortcol': False,
                      # synthetic options
                      'synthetic': False,
                      'compute_post_resample': False,
                      'compute_expression': '',
                      'resample_operation': 'sum',
                      }
    EXTRA_COLUMN_OPTIONS = {}                     # can override in subclass

    def __init__(self, name, **kwargs):
        """ Initialize object. """
        self.slug = '%s_%s' % (self.__class__.__name__, slugify(unicode(name)))
        self.name = name
        self.table = None
        self.columns = []

        # make class vars local to instance
        self.table_options = copy.deepcopy(self.TABLE_OPTIONS)
        self.extra_table_options = copy.deepcopy(self.EXTRA_TABLE_OPTIONS)
        self.table_field_options = copy.deepcopy(self.TABLE_FIELD_OPTIONS)

        self.validate_args(**kwargs)

        # handle custom defaults
        self.pre_process_table()

        self.create_table()
        self.post_process_table()           # add custom fields, etc

    def pre_process_table(self):
        """ Process arguments / defaults before table creation.
        """
        pass

    def validate_args(self, **kwargs):
        """ Process keyword arguments and raise error if invalid items found.
        """
        keys = kwargs.keys()
        tp = dict((k, kwargs.pop(k)) for k in keys if k in self.table_options)
        self.table_options.update(**tp)

        to = dict((k, kwargs.pop(k))
                  for k in keys if k in self.extra_table_options)
        self.extra_table_options.update(**to)

        fp = dict((k, kwargs.pop(k))
                  for k in keys if k in self.table_field_options)
        self.table_field_options.update(**fp)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

    def create_table(self):
        """ Create a datasource table. """

        logger.debug('Creating table %s' % self.slug)

        if self.extra_table_options:
            options = TableDatasourceOptions(default=self.extra_table_options,
                                             **self.extra_table_options)
        else:
            options = None

        self.table = Table.create(name=self.slug, module=self.__module__,
                                  options=options,
                                  **self.table_options)

    def post_process_table(self):
        """ Hook to add custom fields, or other post-table creation operations.
        """
        pass

    def add_column(self, name, label=None, **kwargs):
        """ Create a column object. """
        column_options = copy.deepcopy(self.COLUMN_OPTIONS)
        extra_column_options = copy.deepcopy(self.EXTRA_COLUMN_OPTIONS)

        if label:
            column_options['label'] = label

        keys = kwargs.keys()
        cp = dict((k, kwargs.pop(k)) for k in keys if k in column_options)
        column_options.update(**cp)

        co = dict((k, kwargs.pop(k)) for k in keys if k in extra_column_options)
        extra_column_options.update(**co)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

        if extra_column_options:
            options = ColumnDatasourceOptions(default=extra_column_options,
                                              **extra_column_options)
        else:
            options = None

        c = Column.create(self.table, name, options=options, **column_options)
        self.columns.append(c)
        return c
