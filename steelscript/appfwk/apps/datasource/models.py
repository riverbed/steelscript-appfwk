# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import logging
import traceback
import threading
import time
import hashlib
import importlib
import tokenize
from StringIO import StringIO
import random
import datetime
import string
import copy
import inspect

import pytz
import pandas
import numpy
from django.db import models
from django.db import transaction
from django.db import DatabaseError
from django.db.models import F
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from steelscript.common.jsondict import JsonDict
from steelscript.common.utils import DictObject
from steelscript.common.timeutils import timedelta_total_seconds, tzutc
from steelscript.appfwk.project.utils import (get_module_name, get_sourcefile,
                                              get_namespace)
from steelscript.appfwk.apps.datasource.exceptions import *
from steelscript.appfwk.libs.fields import (PickledObjectField, FunctionField,
                                            SeparatedValuesField,
                                            check_field_choice,
                                            field_choice_str)

logger = logging.getLogger(__name__)

if settings.DATABASES['default']['ENGINE'].endswith('sqlite3'):
    # sqlite doesn't support row locking (select_for_update()), so need
    # to use a threading lock.  This provides support when running
    # the dev server.  It will not work across multiple processes, only
    # between threads of a single process
    lock = threading.RLock()
else:
    lock = None

age_jobs_last_run = 0


class LocalLock(object):
    def __enter__(self):
        if lock is not None:
            lock.acquire()

    def __exit__(self, type, value, traceback):
        if lock is not None:
            lock.release()
        return False


class TableField(models.Model):
    """
    Defines a single field associated with a table.

    TableFields define the the parameters that are used by a Table
    at run time.  The Table.fields attribute associates one
    or more fields with the table.

    At run time, a Criteria object binds values to each field.  The
    Criteria object has an attribute matching each associated TableField
    keyword.

    When defining a TableField, the following model attributes
    may be specified:

    :param keyword: short identifier used like a variable name, this must
        be unique per table

    :param label: text label displayed in user interfaces

    :param help_text: descriptive help text associated with this field

    :param initial: starting or default value to use in user interfaces

    :param required: boolean indicating if a non-null values must be provided

    :param hidden: boolean indicating if this field should be hidden in
        user interfaces, usually true when the value is computed from
        other fields via post_process_func or post_process_template

    :param field_cls: Django Form Field class to use for rendering.
        If not specified, this defaults to CharField

    :param field_kwargs: Dictionary of additional field specific
        kwargs to pass to the field_cls constructor.

    :param parants: List of parent keywords that this field depends on
        for a final value.  Used in conjunction with either
        post_process_func or post_process_template.

    :param pre_process_func: Function to call to perform any necessary
        preprocessing before rendering a form field or accepting
        user input.

    :param post_process_func: Function to call to perform any post
        submit processing.  This may be additional value cleanup
        or computation based on other form data.

    :param post_process_template: Simple string format style template
        to fill in based on other form criteria.
    """
    keyword = models.CharField(max_length=100)
    label = models.CharField(max_length=100, null=True, default=None)
    help_text = models.CharField(blank=True, null=True, default=None, max_length=400)
    initial = PickledObjectField(blank=True, null=True)
    required = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)

    field_cls = PickledObjectField(null=True)
    field_kwargs = PickledObjectField(blank=True, null=True)

    parent_keywords = SeparatedValuesField(null=True)

    pre_process_func = FunctionField(null=True)
    dynamic = models.BooleanField(default=False)
    post_process_func = FunctionField(null=True)
    post_process_template = models.CharField(null=True, max_length=500)

    @classmethod
    def create(cls, keyword, label=None, obj=None, **kwargs):
        parent_keywords = kwargs.pop('parent_keywords', None)
        if parent_keywords is None:
            parent_keywords = []

        field = cls(keyword=keyword, label=label, **kwargs)
        field.save()

        if field.post_process_template is not None:
            f = string.Formatter()
            for (_, parent_keyword, _, _) in f.parse(field.post_process_template):
                if parent_keyword is not None:
                    parent_keywords.append(parent_keyword)

        field.parent_keywords = parent_keywords
        field.save()

        if obj is not None:
            obj.fields.add(field)
        return field

    def __unicode__(self):
        return "<TableField %s (%s)>" % (self.keyword, self.id)

    def __repr__(self):
        return unicode(self)

    def is_report_criteria(self, table):
        """ Runs through intersections of widgets to determine if this criteria
            is applicable to the passed table

            report  <-->  widgets  <-->  table
                |
                L- TableField (self)
        """
        wset = set(table.widget_set.all())
        rset = set(self.report_set.all())
        return any(wset.intersection(set(rwset.widget_set.all())) for rwset in rset)

    @classmethod
    def find_instance(cls, key):
        """ Return instance given a keyword. """
        params = TableField.objects.filter(keyword=key)
        if len(params) == 0:
            return None
        elif len(params) > 1:
            raise KeyError("Multiple TableField matches found for %s"
                           % key)
        param = params[0]
        return param


class Table(models.Model):
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=200)         # source module name
    queryclass = models.CharField(max_length=200)     # name of query class
    datasource = models.CharField(max_length=200)     # class name of datasource
    namespace = models.CharField(max_length=100)
    sourcefile = models.CharField(max_length=200)

    # list of column names
    sortcols = SeparatedValuesField(null=True)

    # list of asc/desc - must match len of sortcols
    sortdir = SeparatedValuesField(null=True)
    # Valid values for sort kwarg
    SORT_NONE = None
    SORT_ASC = 'asc'
    SORT_DESC = 'desc'

    rows = models.IntegerField(default=-1)
    filterexpr = models.CharField(null=True, max_length=400)

    # resample flag -- resample to the criteria.resolution
    # - this requires a "time" column
    resample = models.BooleanField(default=False)

    # options are typically fixed attributes defined at Table creation
    options = PickledObjectField()

    # list of fields that must be bound to values in criteria
    # that this table needs to run
    fields = models.ManyToManyField(TableField, null=True)

    # Default values for fields associated with this table, these
    # may be overridden by user criteria at run time
    criteria = PickledObjectField()

    # Function to call to tweak criteria for computing a job handle.
    # This must return a dictionary of key/value pairs of values
    # to use for computing a determining when a job must be rerun.
    criteria_handle_func = FunctionField(null=True)

    # Indicates if data can be cached
    cacheable = models.BooleanField(default=True)

    @classmethod
    def to_ref(cls, arg):
        """ Generate a table reference.

        :param arg: may be either a Table object, table id,
            or dictionary reference.

        """

        if isinstance(arg, dict):
            if 'namespace' not in arg or 'name' not in arg:
                raise KeyError('Invalid table ref as dict, expected namespace/name')
            return arg

        if isinstance(arg, Table):
            table = arg
        elif hasattr(arg, 'table'):
            # Datasource table
            table = arg.table
        elif isinstance(arg, int):
            table = Table.objects.get(id=arg)
        else:
            raise ValueError('No way to handle Table arg of type %s' % type(arg))
        return {'sourcefile': table.sourcefile,
                'namespace': table.namespace,
                'name': table.name}

    @classmethod
    def from_ref(cls, ref):
        return Table.objects.get(sourcefile=ref['sourcefile'],
                                 namespace=ref['namespace'],
                                 name=ref['name'])

    def __unicode__(self):
        return "<Table %s (%s)>" % (str(self.id), self.name)

    def __repr__(self):
        return unicode(self)

    def get_columns(self, synthetic=None, ephemeral=None, iskey=None):
        """
        Return the list of columns for this table.

        `synthetic` is tri-state: None (default) is don't care,
            True means only synthetic columns, False means
            only non-synthetic columns

        `ephemeral` is a job reference.  If specified, include
            ephemeral columns related to this job

        `iskey` is tri-state: None (default) is don't care,
            True means only key columns, False means
            only non-key columns

        """

        filtered = []
        for c in Column.objects.filter(table=self).order_by('position', 'name'):
            if synthetic is not None and c.synthetic != synthetic:
                continue
            if c.ephemeral is not None and c.ephemeral != ephemeral:
                continue
            if iskey is not None and c.iskey != iskey:
                continue
            filtered.append(c)

        return filtered

    def copy_columns(self, table, columns=None, except_columns=None):
        """ Copy the columns from `table` into this table.

        This method will copy all the columns from another table, including
        all attributes as well as sorting.

        """

        if not isinstance(table, Table):
            table = Table.from_ref(table)

        sortcols = []
        sortdir = []
        for c in table.get_columns():
            if columns is not None and c.name not in columns:
                continue
            if except_columns is not None and c.name in except_columns:
                continue

            if table.sortcols and (c.name in table.sortcols):
                sortcols.append(c.name)
                sortdir.append(table.sortdir[table.sortcols.index(c.name)])

            c.pk = None
            c.table = self
            c.position = Column.get_position()

            c.save()

        if sortcols:
            self.sortcols = sortcols
            self.sortdir = sortdir
            self.save()

    def compute_synthetic(self, job, df):
        """ Compute the synthetic columns from DF a two-dimensional array
            of the non-synthetic columns.

            Synthesis occurs as follows:

            1. Compute all synthetic columns where compute_post_resample
               is False

            2. If the table is a time-based table with a defined resolution, the
               result is resampled.

            3. Any remaining columns are computed.
        """
        if df is None:
            return None

        all_columns = job.get_columns()
        all_col_names = [c.name for c in all_columns]

        def compute(df, syncols):
            #logger.debug("Compute: syncol = %s" % ([c.name for c in syncols]))
            for syncol in syncols:
                expr = syncol.compute_expression
                g = tokenize.generate_tokens(StringIO(expr).readline)
                newexpr = ""
                getvalue = False
                getclose = False
                for ttype, tvalue, _, _, _ in g:
                    if getvalue:
                        if ttype != tokenize.NAME:
                            msg = "Invalid syntax, expected {name}: %s" % tvalue
                            raise ValueError(msg)
                        elif tvalue not in all_col_names:
                            raise ValueError("Invalid column name: %s" % tvalue)
                        newexpr += "df['%s']" % tvalue
                        getclose = True
                        getvalue = False
                    elif getclose:
                        if ttype != tokenize.OP and tvalue != "}":
                            msg = "Invalid syntax, expected {name}: %s" % tvalue
                            raise ValueError(msg)
                        getclose = False
                    elif ttype == tokenize.OP and tvalue == "{":
                        getvalue = True
                    else:
                        newexpr += tvalue

                df[syncol.name] = eval(newexpr)

        # 1. Compute synthetic columns where post_resample is False
        compute(df, [col for col in all_columns if (col.synthetic and
                                                    col.compute_post_resample is False)])

        # 2. Resample
        colmap = {}
        timecol = None
        for col in all_columns:
            colmap[col.name] = col
            if col.istime():
                timecol = col.name

        if self.resample:
            if timecol is None:
                raise (TableComputeSyntheticError
                       ("Table %s 'resample' is set but no 'time' column'" %
                        self))

            if (  ('resolution' not in job.criteria) and
                  ('resample_resolution' not in job.criteria)):
                raise (TableComputeSyntheticError
                       (("Table %s 'resample' is set but criteria missing " +
                         "'resolution' or 'resample_resolution'") % self))

            how = {}
            for k in df.keys():
                if k == timecol:
                    continue
                how[k] = colmap[k].resample_operation

            if 'resample_resolution' in job.criteria:
                resolution = job.criteria.resample_resolution
            else:
                resolution = job.criteria.resolution

            resolution = timedelta_total_seconds(resolution)
            if resolution < 1:
                raise (TableComputeSyntheticError
                       (("Table %s cannot resample at a resolution " +
                         "less than 1 second") % self))

            logger.debug('%s: resampling to %ss' % (self, int(resolution)))

            indexed = df.set_index(timecol)
            # XXX pandas 0.13.1 drops timezones when moving time cols around
            # take timezone of first value from timecol, if there is one
            if df[timecol][0].tz:
                indexed.index = indexed.index.tz_localize(df[timecol][0].tz)

            #indexed.to_pickle('/tmp/indexed.pd')
            #df.to_pickle('/tmp/df.pd')

            resampled = indexed.resample('%ss' % int(resolution), how,
                                         convention='end').reset_index()
            df = resampled

        # 3. Compute remaining synthetic columns (post_resample is True)
        compute(df, [c for c in all_columns
                     if (c.synthetic and c.compute_post_resample is True)])

        return df



class DatasourceTable(Table):

    class Meta:
        proxy = True

    TABLE_OPTIONS = {}
    FIELD_OPTIONS = {}

    _column_class = None  # override in subclass if needed, defaults to Column
    _query_class = 'TableQuery'

    def __init__(self, *args, **kwargs):
        super(DatasourceTable, self).__init__(*args, **kwargs)

    @classmethod
    def create(cls, name, **kwargs):
        """Create a table.

        :param str name: Unique identifier for this table

        Standard keyword arguments:

        :param int rows: set maximum number of rows to save after
            sorting (defaults to -1, no maximum)

        :param bool resample: if True, timeseries data returned by the
            data source will be resampled to ``criteria.resample_resolution``
            or ``criteria.resolution``

        :param dict field_map: a dictionary mapping fields by keyword
            to either a new keyword or to a map of field values to
            customize for the given field

                field_map = {'qos': 'qos_1'}

            or

                field_map = {'qos': { 'keyword': 'qos_1',
                                      'label': 'QoS 1',
                                      'default': 'AF' } }

            This is used to remap fields defined by standard tables
            to allow the same table to be used multiple times in the
            same report but with different criteria via different
            keywords.

        Additional table and field options keyword arguments may
        be provided that are unique to the specific data source
        table being instantiatied:

        ``table_options``

            These options define subclass-specific options that allow
            customization of a table instance. Table options are *not*
            visible to users running reports via the UI.  Option
            values are provided at table creation and are considered
            static for the life of this table instance.

        ``field_options``

            Most tables are designed to take input from the user via table
            fields.  The user fills in values for each table field and the set
            of input becomes the report *criteria*.

            Field options allow the report writer to customize the aspects of
            table fields such as the initial value of a form field or the list
            of choices in a drop-down selection field.

        """
        name = slugify(unicode(name))

        # process subclass assigned options
        table_options = copy.deepcopy(cls.TABLE_OPTIONS)
        field_options = copy.deepcopy(cls.FIELD_OPTIONS)

        if hasattr(cls, '_ANALYSIS_TABLE_OPTIONS'):
            table_options.update(cls._ANALYSIS_TABLE_OPTIONS)
            field_options.update(cls._ANALYSIS_FIELD_OPTIONS)

        keys = kwargs.keys()

        # The field_map mapping is stored in table_options for reference
        # later when building criteria for this table
        table_options['field_map'] = {}
        to = dict((k, kwargs.pop(k)) for k in keys if k in table_options)
        table_options.update(**to)

        fo = dict((k, kwargs.pop(k)) for k in keys if k in field_options)
        field_options.update(**fo)

        table_options = cls.process_options(table_options)

        if table_options:
            options = JsonDict(default=table_options)
        else:
            options = None

        # process normal model kwargs
        keys = kwargs.keys()
        tkeys = [f.name for f in Table._meta.local_fields]
        table_kwargs = dict((k, kwargs.pop(k)) for k in keys if k in tkeys)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

        queryclass = cls._query_class
        if inspect.isclass(queryclass):
            queryclass = queryclass.__name__

        sourcefile = get_sourcefile(get_module_name())
        namespace = get_namespace(sourcefile)

        if len(Table.objects.filter(name=name,
                                    namespace=namespace,
                                    sourcefile=sourcefile)) > 0:
            raise ValueError(("Table '%s' already exists in namespace '%s' "
                             "(sourcefile '%s')") % (name, namespace, sourcefile))

        logger.debug('Creating table %s' % name)
        t = cls(name=name, module=cls.__module__, queryclass=queryclass,
                datasource=cls.__name__, options=options,
                sourcefile=sourcefile, namespace=namespace, **table_kwargs)
        try:
            t.save()
        except DatabaseError as e:
            if 'no such table' in str(e):
                raise DatabaseError(str(e) + ' -- did you forget class Meta: proxy=True?')
            raise

        # post process table *instance* now that its been initialized
        t.post_process_table(field_options)

        # if field_map has been specified, go through attached fields and
        # change them accordingly
        for keyword, mapped in (t.options.field_map or {}).iteritems():
            try:
                field = t.fields.get(keyword=keyword)
                if isinstance(mapped, basestring):
                    field.keyword = mapped
                else:
                    for k, v in mapped.iteritems():
                        if not hasattr(field, k):
                            raise AttributeError(
                                "Invalid attribute for field '%s': %s" %
                                (field.keyword, k))
                        setattr(field, k, v)

                field.save()
            except ObjectDoesNotExist:
                raise AttributeError(
                    'field_map references invalid field: %s' % keyword)

        return t

    @classmethod
    def process_options(cls, table_options):
        """ Hook to process options before Table saved to database.
        """
        return table_options

    def post_process_table(self, field_options):
        """ Hook to add custom fields, or other post-table creation operations.
        """
        pass

    def add_column(self, name, label=None,
                   sortasc=False, sortdesc=False, **kwargs):
        """Add a column to this table.

        :param str name: Unique identifier for this column
        :param str label: Display string, defaults to name
        :param bool sortasc, sortdesc: Sort table based on this columns data

        Standard keyword arguments:

        :param bool iskey: Set True for key columns

        :param enum datatype: type of data his column contains,
            defaults to 'float':

            * float
            * integer
            * time
            * string
            * html

        :param enum units: Units for data in this column, defaults to none:

            * none - no units
            * s - seconds
            * ms - milliseconds
            * B - bytes
            * B/s - bytes per second
            * pct - percentage

        :param float position: Display position relative to other columns, automatically
            computed by default

        :param bool synthetic: Set True to compute this columns value
            according to ``compute_expression``

        :param str compute_expression: Computation expression for syntetic columns

        :param bool compute_post_resample: If true, compute this synthetic column
            after resampling (time series only)

        :param str resample_operation: Operation to use on this column to aggregate
            multiple rows during resampling, defaults to sum


        """
        columnclass = self._column_class or Column
        if not inspect.isclass(columnclass):
            m = importlib.import_module(self.module)
            columnclass = m.__dict__[columnclass]

        c = columnclass.create(self, name, label, **kwargs)

        if sortasc or sortdesc:
            if self.sortcols is None:
                self.sortcols = [c.name]
            else:
                self.sortcols.append(c.name)

            if sortasc and sortdesc:
                raise AttributeError('Cannot set both sortasc and sortdesc')

            sortdir = Table.SORT_ASC if sortasc else Table.SORT_DESC
            if self.sortdir is None:
                self.sortdir = [sortdir]
            else:
                self.sortdir.append(sortdir)

            self.save()

        return c


class Column(models.Model):

    table = models.ForeignKey(Table)
    name = models.CharField(max_length=300)
    label = models.CharField(max_length=300, null=True)
    position = models.DecimalField(max_digits=7, decimal_places=3, default=1)
    options = PickledObjectField()

    iskey = models.BooleanField(default=False)

    synthetic = models.BooleanField(default=False)

    # Ephemeral columns are columns added to a table at run-time
    ephemeral = models.ForeignKey('Job', null=True)

    compute_post_resample = models.BooleanField(default=False)
    compute_expression = models.CharField(max_length=300)
    resample_operation = models.CharField(max_length=300, default='sum')

    DATATYPE_FLOAT = 0
    DATATYPE_INTEGER = 1
    DATATYPE_TIME = 2
    DATATYPE_STRING = 3
    DATATYPE_HTML = 4

    datatype = models.IntegerField(
        default=DATATYPE_FLOAT,
        choices=((DATATYPE_FLOAT, "float"),
                 (DATATYPE_INTEGER, "integer"),
                 (DATATYPE_TIME, "time"),
                 (DATATYPE_STRING, "string"),
                 (DATATYPE_HTML, "html"))
    )

    UNITS_NONE = 0
    UNITS_SECS = 1
    UNITS_MSECS = 2
    UNITS_BYTES = 3
    UNITS_BYTES_PER_SEC = 4
    UNITS_PCT = 5
    units = models.IntegerField(
        default=UNITS_NONE,
        choices=((UNITS_NONE, "none"),
                 (UNITS_SECS, "s"),
                 (UNITS_MSECS, "ms"),
                 (UNITS_BYTES, "B"),
                 (UNITS_BYTES_PER_SEC, "B/s"),
                 (UNITS_PCT, "pct"))
    )

    # default options to populate options field
    COLUMN_OPTIONS = {}
    POS_MAX = 0

    def __unicode__(self):
        return "<Column %s (%s)>" % (str(self.id), self.name)

    def __repr__(self):
        return unicode(self)

    def save(self, *args, **kwargs):
        if self.label is None:
            self.label = self.name
        super(Column, self).save()

    @classmethod
    def get_position(cls):
        """ Get position value to use for model object. """

        # This value will reset on server restarts or when the class goes
        # out of scope/reloaded, but since we are only looking for positions
        # relative to other columns in a given table, we don't need
        # to be too precise.
        cls.POS_MAX += 1
        return cls.POS_MAX

    @classmethod
    def create(cls, table, name, label=None,
               datatype=DATATYPE_FLOAT, units=UNITS_NONE,
               iskey=False, **kwargs):

        column_options = copy.deepcopy(cls.COLUMN_OPTIONS)

        keys = kwargs.keys()
        cp = dict((k, kwargs.pop(k)) for k in keys if k in column_options)
        column_options.update(**cp)

        if column_options:
            options = JsonDict(default=column_options)
        else:
            options = None

        keys = kwargs.keys()
        ckeys = [f.name for f in Column._meta.local_fields]
        col_kwargs = dict((k, kwargs.pop(k)) for k in keys if k in ckeys)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

        ephemeral = col_kwargs.get('ephemeral', None)
        if len(Column.objects.filter(table=table, name=name,
                                     ephemeral=ephemeral)) > 0:
            raise ValueError("Column %s already in use for table %s" %
                             (name, str(table)))

        datatype = check_field_choice(cls, 'datatype', datatype)
        units = check_field_choice(cls, 'units', units)

        c = Column(table=table, name=name, label=label, datatype=datatype,
                   units=units, iskey=iskey, options=options, **col_kwargs)

        c.position = cls.get_position()
        try:
            c.save()
        except DatabaseError as e:
            if 'no such table' in str(e):
                raise DatabaseError(str(e) + ' -- did you forget class Meta: proxy=True?')
            raise


        return c

    def isnumeric(self):
        return self.datatype in [self.DATATYPE_FLOAT, self.DATATYPE_INTEGER]

    def istime(self):
        return self.datatype == self.DATATYPE_TIME

    def units_str(self):
        if self.units == self.UNITS_NONE:
            return None
        return field_choice_str(self, 'units', self.units)


class Criteria(DictObject):
    """ Manage a collection of criteria values. """
    def __init__(self, **kwargs):
        """ Initialize a criteria object based on key/value pairs. """

        self.starttime = None
        self.endtime = None
        self.duration = None

        super(Criteria, self).__init__(kwargs)

        #self.filterexpr = filterexpr
        #self.ignore_cache = ignore_cache

        # Keep track of the original starttime / endtime
        # This are needed when recomputing start/end times with
        # different default durations
        self._orig_starttime = self.starttime
        self._orig_endtime = self.endtime
        self._orig_duration = self.duration

    def __setattr__(self, key, value):
        self[key] = value
        if key.startswith('_'):
            return
        elif key in ['starttime', 'endtime', 'duration']:
            self['_orig_%s' % key] = value
        #else:
        #    param = TableField.find_instance(key)
        #    if param.initial != value:
        #        param.initial = value
        #        param.save()

    def print_details(self):
        """ Return instance variables as nicely formatted string
        """
        return ', '.join([("%s: %s" % (k, v)) for k, v in self.iteritems()])

    def build_for_table(self, table):
        """ Build a criteria object for a table.

        This copies over all criteria parameters but has
        special handling for starttime, endtime, and duration,
        as they may be altered if duration is 'default'.

        In addition, if this table has a field_map, the incoming criteria
        is using the mapped keyword, but the underlying tables expect the
        original keyword so reverse the mapping.

        """
        crit = Criteria(starttime=self._orig_starttime,
                        endtime=self._orig_endtime,
                        duration=self._orig_duration)

        field_map = (table.options.field_map or {})
        rev_field_map = {}
        for k, v in field_map.iteritems():
            if not isinstance(v, basestring):
                if 'keyword' in v:
                    v = v['keyword']
                else:
                    v = k
            rev_field_map[v] =k

        for k, v in self.iteritems():
            if k in ['starttime', 'endtime', 'duration'] or k.startswith('_'):
                continue

            # Note, this problably needs work to support customizing
            # starttime/endtime/duration
            if k in rev_field_map:
                k = rev_field_map[k]

            crit[k] = v

        return crit

    def compute_times(self):
        # Start with the original values not any values formerly computed
        duration = self._orig_duration
        starttime = self._orig_starttime
        endtime = self._orig_endtime

        logger.debug("compute_times: %s %s %s" %
                     (starttime, endtime, duration))

        if starttime is not None:
            if endtime is not None:
                duration = endtime - starttime
            elif duration is not None:
                endtime = starttime + duration
            else:
                msg = ("Cannot compute times, have starttime but not "
                       "endtime or duration")
                raise ValueError(msg)

        elif endtime is None:
            endtime = datetime.datetime.now()

        if duration is not None:
            starttime = endtime - duration
        else:
            msg = ("Cannot compute times, have endtime but not "
                   "starttime or duration")
            raise ValueError(msg)

        self.duration = duration
        self.starttime = starttime
        self.endtime = endtime


class TableQueryBase(object):
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def __unicode__(self):
        return "<%s %s>" % (self.__class__.__name__, self.job)

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self.job)

    def mark_progress(self, progress):
        # Called by the analysis function
        tables = getattr(self.table.options, 'tables', None)
        if tables:
            n = len(tables)+1
        else:
            n = 1
        self.job.mark_progress(((n-1)*100 + progress)/n)

    def pre_run(self):
        return True

    def run(self):
        return True

    def post_run(self):
        return True


class Job(models.Model):

    # Timestamp when the job was created
    created = models.DateTimeField(auto_now_add=True)

    # Timestamp the last time the job was accessed
    touched = models.DateTimeField(auto_now_add=True)

    # Number of references to this job
    refcount = models.IntegerField(default=0)

    # Whether this job is a child of another job
    ischild = models.BooleanField(default=False)

    # If ischild, this points to the parent job
    parent = models.ForeignKey('self', null=True)

    # Table associated with this job
    table = models.ForeignKey(Table)

    # Criteria used to start this job - an instance of the Criteria class
    criteria = PickledObjectField(null=True)

    # Actual criteria as returned by the job after running
    actual_criteria = PickledObjectField(null=True)

    # Unique handle for the job
    handle = models.CharField(max_length=100, default="")

    # Job status
    NEW = 0
    RUNNING = 1
    COMPLETE = 3
    ERROR = 4

    status = models.IntegerField(
        default=NEW,
        choices=((NEW, "New"),
                 (RUNNING, "Running"),
                 (COMPLETE, "Complete"),
                 (ERROR, "Error")))

    # Message if job complete or error
    message = models.TextField(default="")

    # While RUNNING, this provides an indicator of progress 0-100
    progress = models.IntegerField(default=-1)

    # While RUNNING, time remaining
    remaining = models.IntegerField(default=None, null=True)

    def __unicode__(self):
        return "<Job %s (%8.8s) - t%s>" % (self.id, self.handle, self.table.id)

    def __repr__(self):
        return unicode(self)

    def refresh(self):
        """ Refresh dynamic job parameters from the database. """
        job = Job.objects.get(pk=self.pk)
        for k in ['status', 'message', 'progress', 'remaining',
                  'actual_criteria', 'touched', 'refcount']:
            setattr(self, k, getattr(job, k))

    @transaction.commit_on_success
    def safe_update(self, **kwargs):
        """ Update the job with the passed dictionary in a database safe way.

        This method updates only the requested paraemters and refreshes
        the rest from the database.  This should be used for all updates
        to Job's to ensure that unmodified keys are not accidentally
        clobbered by doing a blanket job.save().

        """

        if kwargs is None:
            return

        with LocalLock():
            #logger.debug("%s safe_update %s" % (self, kwargs))
            Job.objects.filter(pk=self.pk).update(**kwargs)

            # Force a reload of the job to get latest data
            self.refresh()

            if not self.ischild:
                # Push changes to children of this job
                child_kwargs = {}
                for k, v in kwargs.iteritems():
                    if k in ['status', 'message', 'progress', 'remaining',
                             'actual_criteria']:
                        child_kwargs[k] = v
                # There should be no recursion, so a direct update to the
                # database is possible.  (If recursion, would need to call
                # self_update() on each child.)
                Job.objects.filter(parent=self).update(**child_kwargs)

    @classmethod
    def create(cls, table, criteria):

        with LocalLock():
            with transaction.commit_on_success():
                # Grab a lock on the row associated with the table
                table = Table.objects.select_for_update().get(id=table.id)

                criteria = criteria.build_for_table(table)
                # Lockdown start/endtimes
                try:
                    criteria.compute_times()
                except ValueError:
                    # Ignore errors, this table may not have start/end times
                    pass

                # Compute the handle -- this will take into account
                # cacheability
                handle = Job._compute_handle(table, criteria)

                # Look for another job by the same handle in any state
                # except ERROR
                if not criteria.ignore_cache:
                    parents = (Job.objects
                               .select_for_update()
                               .filter(status__in=[Job.NEW,
                                                   Job.COMPLETE,
                                                   Job.RUNNING],
                                       handle=handle,
                                       ischild=False)
                               .order_by('created'))
                else:
                    parents = None

                if parents is not None and len(parents) > 0:
                    parent = parents[0]

                    job = Job(table=table,
                              criteria=criteria,
                              actual_criteria=parent.actual_criteria,
                              status=parent.status,
                              handle=handle,
                              parent=parent,
                              ischild=True,
                              progress=parent.progress,
                              remaining=parent.remaining,
                              message='')
                    job.save()

                    parent.reference("Link from job %s" % job)
                    now = datetime.datetime.now(tz=pytz.utc)
                    parent.safe_update(touched=now)

                    logger.info("%s: New job for table %s, linked to parent %s"
                                % (job, table.name, parent))
                else:
                    job = Job(table=table,
                              criteria=criteria,
                              status=Job.NEW,
                              handle=handle,
                              parent=None,
                              ischild=False,
                              progress=0,
                              remaining=-1,
                              message='')
                    job.save()
                    logger.info("%s: New job for table %s" % (job, table.name))

                logger.debug("%s: criteria = %s" % (job, criteria))

            # Flush old jobs
            Job.age_jobs()

        return job

    @classmethod
    def _compute_handle(cls, table, criteria):
        h = hashlib.md5()
        h.update(str(table.id))

        if table.cacheable and not criteria.ignore_cache:
            # XXXCJ - Drop ephemeral columns when computing the cache handle,
            # since the list of columns is modifed at run time.   Typical use
            # case is an analysis table which creates a time-series graph of
            # the top 10 hosts -- one column per host.  The host columns will
            # change based on the run of the dependent table.
            #
            # Including epheremal columns causes some problems because the
            # handle is computed before the query is actually run, so it never
            # matches.
            #
            # May want to dig in to this further and make sure this doesn't
            # pick up cache files when we don't want it to
            h.update('.'.join([c.name for c in
                               table.get_columns()]))

            if table.criteria_handle_func:
                criteria = table.criteria_handle_func(criteria)

            for k, v in criteria.iteritems():
                #logger.debug("Updating hash from %s -> %s" % (k,v))
                h.update('%s:%s' % (k, v))
        else:
            # Table is not cacheable, instead use current time plus a random
            # value just to get a unique hash
            h.update(str(datetime.datetime.now()))
            h.update(str(random.randint(0, 10000000)))

        return h.hexdigest()

    def reference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')+1)
        #logger.debug("%s: reference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def dereference(self, message=""):
        pk = self.pk
        Job.objects.filter(pk=pk).update(refcount=F('refcount')-1)
        #logger.debug("%s: dereference(%s) @ %d" %
        #             (self, message, Job.objects.get(pk=pk).refcount))

    def get_columns(self, ephemeral=None, **kwargs):
        """ Return columns assocated with the table for the job.

        The returned column set includes ephemeral columns associated
        with this job unless ephemeral is set to False.

        """
        if ephemeral is None:
            kwargs['ephemeral'] = self.parent or self
        return self.table.get_columns(**kwargs)

    def json(self, data=None):
        """ Return a JSON represention of this Job. """
        return {'id': self.id,
                'handle': self.handle,
                'progress': self.progress,
                'remaining': self.remaining,
                'status': self.status,
                'message': self.message,
                'data': data}

    def combine_filterexprs(self, joinstr="and", exprs=None):
        self.refresh()

        criteria = self.criteria
        if exprs is None:
            exprs = []
        elif type(exprs) is not list:
            exprs = [exprs]

        exprs.append(self.table.filterexpr)

        nonnull_exprs = []
        for e in exprs:
            if e != "" and e is not None:
                nonnull_exprs.append(e)

        if len(nonnull_exprs) > 1:
            return "(" + (") " + joinstr + " (").join(nonnull_exprs) + ")"
        elif len(nonnull_exprs) == 1:
            return nonnull_exprs[0]
        else:
            return ""

    def start(self):
        """ Start this job. """

        self.refresh()

        if self.ischild:
            logger.debug("%s: Shadowing parent job %s" % (self, self.parent))
            return

        with transaction.commit_on_success():
            logger.debug("%s: Starting job" % str(self))
            self.mark_progress(0)

            logger.debug("%s: Worker to run report" % str(self))
            # Lookup the query class for this table
            i = importlib.import_module(self.table.module)
            queryclass = i.__dict__[self.table.queryclass]

            # Create an worker to do the work
            worker = Worker(self, queryclass)
            worker.start()

    def mark_error(self, message):
        logger.warning("%s failed: %s" % (self, message))
        self.safe_update(status=Job.ERROR,
                         progress=100,
                         message=message)

    def mark_complete(self):
        logger.info("%s complete" % self)
        self.safe_update(status=Job.COMPLETE,
                         progress=100,
                         message='')

    def mark_progress(self, progress, remaining=None):
        #logger.debug("%s progress %s" % (self, progress))
        self.safe_update(status=Job.RUNNING,
                         progress=progress,
                         remaining=remaining)

    def datafile(self):
        """ Return the data file for this job. """
        return os.path.join(settings.DATA_CACHE, "job-%s.data" % self.handle)

    def data(self):
        """ Returns a pandas.DataFrame of data, or None if not available. """

        with transaction.commit_on_success():
            self.refresh()
            if not self.status == Job.COMPLETE:
                raise ValueError("Job not complete, no data available")

            self.reference("data()")

            e = None
            try:
                logger.debug("%s looking for data file: %s" %
                             (str(self), self.datafile()))
                if os.path.exists(self.datafile()):
                    df = pandas.read_pickle(self.datafile())
                    logger.debug("%s data loaded %d rows from file: %s" %
                                 (str(self), len(df), self.datafile()))
                else:
                    logger.debug("%s no data, missing data file: %s" %
                                 (str(self), self.datafile()))
                    df = None
            except Exception as e:
                logger.error("Error loading datafile %s for %s" %
                             (self.datafile(), str(self)))
                logger.error("Traceback:\n%s" % e)
            finally:
                self.dereference("data()")

            if e:
                raise e

            return df

    def values(self):
        """ Return data as a list of lists. """

        df = self.data()
        if df is not None:
            # Replace NaN with None
            df = df.where(pandas.notnull(df), None)

            # Extract tha values in the right order
            all_columns = self.get_columns()
            all_col_names = [c.name for c in all_columns]

            # Straggling numpy data types may cause problems
            # downstream (json encoding, for example), so strip
            # things down to just native ints and floats
            vals = []
            for row in df.ix[:, all_col_names].itertuples():
                vals_row = []
                for v in row[1:]:
                    if (isinstance(v, numpy.number) or
                            isinstance(v, numpy.bool_)):
                        v = numpy.asscalar(v)
                    vals_row.append(v)
                vals.append(vals_row)

        else:
            vals = []
        return vals

    @classmethod
    def age_jobs(cls, old=None, ancient=None, force=False):
        """ Delete old jobs that have no refcount and all ancient jobs. """
        # Throttle - only run this at most once every 15 minutes
        global age_jobs_last_run
        if not force and time.time() - age_jobs_last_run < 60*15:
            return

        age_jobs_last_run = time.time()

        if old is None:
            old = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_old_seconds']
            )
        elif type(old) in [int, float]:
            old = datetime.timedelta(seconds=old)

        if ancient is None:
            ancient = datetime.timedelta(
                seconds=settings.APPS_DATASOURCE['job_age_ancient_seconds']
            )
        elif type(ancient) in [int, float]:
            ancient = datetime.timedelta(seconds=ancient)

        with transaction.commit_on_success():
            # Ancient jobs are deleted regardless of refcount
            now = datetime.datetime.now(tz=pytz.utc)
            try:
                qs = (Job.objects.select_for_update().
                      filter(touched__lte=now - ancient))
                if len(qs) > 0:
                    logger.info('Deleting %d ancient jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete ancient jobs")

            # Old jobs are deleted only if they have a refcount of 0
            try:
                qs = (Job.objects.select_for_update().
                      filter(touched__lte=now - old, refcount=0))
                if len(qs) > 0:
                    logger.info('Deleting %d old jobs ...' % len(qs))
                    qs.delete()
            except:
                logger.exception("Failed to delete old jobs")

    @classmethod
    def flush_incomplete(cls):
        jobs = Job.objects.filter(progress__lt=100)
        logger.info("Flushing %d incomplete jobs: %s" %
                    (len(jobs), [j.id for j in jobs]))
        jobs.delete()

    def done(self):
        self.refresh()
        #logger.debug("%s status: %s - %s%%" % (str(self),
        #                                       self.status,
        #                                       self.progress))
        return self.status == Job.COMPLETE or self.status == Job.ERROR


@receiver(pre_delete, sender=Job)
def _my_job_delete(sender, instance, **kwargs):
    """ Clean up jobs when deleting. """
    # if a job has a parent, just deref, don't delete the datafile since
    # that will remove it from the parent as well
    if instance.parent is not None:
        instance.parent.dereference(str(instance))
    elif instance.datafile() and os.path.exists(instance.datafile()):
        try:
            os.unlink(instance.datafile())
        except OSError:
            # permissions issues, perhaps
            logger.error('OSError occurred when attempting to delete '
                         'job datafile: %s' % instance.datafile())


class AsyncWorker(threading.Thread):
    def __init__(self, job, queryclass):
        threading.Thread.__init__(self)
        self.daemon = True
        self.job = job
        self.queryclass = queryclass

        logger.info("%s created" % self)
        job.reference("AsyncWorker created")

    def __delete__(self):
        if self.job:
            self.job.dereference("AsyncWorker deleted")

    def __unicode__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __str__(self):
        return "<AsyncWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def run(self):
        self.do_run()
        sys.exit(0)


class SyncWorker(object):
    def __init__(self, job, queryclass):
        self.job = job
        self.queryclass = queryclass

    def __unicode__(self):
        return "<SyncWorker %s>" % (self.job)

    def __str__(self):
        return "<SyncWorker %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        self.do_run()

if settings.APPS_DATASOURCE['threading'] and not settings.TESTING:
    base_worker_class = AsyncWorker
else:
    base_worker_class = SyncWorker


class Worker(base_worker_class):

    def __init__(self, job, queryclass):
        super(Worker, self).__init__(job, queryclass)

    def do_run(self):
        job = self.job
        try:
            logger.info("%s running queryclass %s" % (self, self.queryclass))
            query = self.queryclass(job.table, job)

            if (  query.pre_run() and
                  query.run() and
                  query.post_run()):

                logger.info("%s query finished" % self)
                if isinstance(query.data, list) and len(query.data) > 0:
                    # Convert the result to a dataframe
                    columns = [col.name for col in
                               job.get_columns(synthetic=False)]
                    df = pandas.DataFrame(query.data, columns=columns)
                elif ((query.data is None) or
                      (isinstance(query.data, list) and len(query.data) == 0)):
                    df = None
                elif isinstance(query.data, pandas.DataFrame):
                    df = query.data
                else:
                    raise ValueError("Unrecognized query result type: %s" %
                                     type(query.data))

                if df is not None:
                    self.check_columns(df)
                    df = self.normalize_types(df)
                    df = job.table.compute_synthetic(job, df)

                    # Sort according to the defined sort columns
                    if job.table.sortcols:
                        sorted = df.sort(job.table.sortcols,
                                         ascending=[b == Table.SORT_ASC
                                                    for b in job.table.sortdir])
                        # Move NaN rows of the first sortcol to the end
                        n = job.table.sortcols[0]
                        df = (sorted[sorted[n].notnull()]
                              .append(sorted[sorted[n].isnull()]))

                    if job.table.rows > 0:
                        df = df[job.table.rows]

                if df is not None:
                    df.to_pickle(job.datafile())
                    logger.debug("%s data saved to file: %s" % (str(self),
                                                                job.datafile()))
                else:
                    logger.debug("%s no data saved, data is empty" %
                                 (str(self)))

                logger.info("%s finished as COMPLETE" % self)
                job.refresh()
                if job.actual_criteria is None:
                    job.safe_update(actual_criteria=job.criteria)

                job.mark_complete()
            else:
                # If the query.run() function returns false, the run() may
                # have set the job.status, check and update if not
                vals = {}
                job.refresh()
                if not job.done():
                    vals['status'] = job.ERROR
                if job.message == "":
                    vals['message'] = "Query returned an unknown error"
                vals['progress'] = 100
                job.safe_update(**vals)
                logger.error("%s finished with an error: %s" % (self,
                                                                job.message))

        except:
            logger.exception("%s raised an exception" % self)
            job.safe_update(
                status=job.ERROR,
                progress=100,
                message=traceback.format_exception_only(sys.exc_info()[0],
                                                        sys.exc_info()[1])
            )

        finally:
            job.dereference("Worker exiting")

    def check_columns(self, df):
        job = self.job
        for col in job.get_columns(synthetic=False):
            if col.name not in df:
                raise ValueError(
                    'Returned table missing expected column: %s' % col.name)

    def normalize_types(self, df):
        job = self.job
        for col in job.get_columns(synthetic=False):
            s = df[col.name]
            if col.istime():
                # The column is supposed to be time,
                # make sure all values are datetime objects
                if str(s.dtype).startswith(str(pandas.np.dtype('datetime64'))):
                    # Already a datetime
                    pass
                elif str(s.dtype).startswith('int'):
                    # Assume this is a numeric epoch, convert to datetime
                    df[col.name] = s.astype('datetime64[s]')
                elif str(s.dtype).startswith('float'):
                    # This is a numeric epoch as a float, possibly
                    # has subsecond resolution, convert to
                    # datetime but preserve up to millisecond
                    df[col.name] = (1000 * s).astype('datetime64[ms]')
                else:
                    # Possibly datetime object or a datetime string,
                    # hopefully astype() can figure it out
                    df[col.name] = s.astype('datetime64[ms]')

                # Make sure we are UTC, must use internal tzutc because
                # pytz timezones will cause an error when unpickling
                # https://github.com/pydata/pandas/issues/6871
                try:
                    df[col.name] = df[col.name].apply(lambda x:
                                                      x.tz_localize(tzutc()))
                except BaseException as e:
                    if e.message.startswith('Cannot convert'):
                        df[col.name] = df[col.name].apply(lambda x:
                                                          x.tz_convert(tzutc()))
                    else:
                        raise

            elif (col.isnumeric() and
                  s.dtype == pandas.np.dtype('object')):
                # The column is supposed to be numeric but must have
                # some strings.  Try replacing empty strings with NaN
                # and see if it converts to float64
                try:
                    df[col.name] = (s.replace('', pandas.np.NaN)
                                    .astype(pandas.np.float64))
                except ValueError:
                    # This may incorrectly be tagged as numeric
                    pass

        return df


class BatchJobRunner(object):

    def __init__(self, basejob, batchsize=4, min_progress=0, max_progress=100):
        self.basejob = basejob
        self.jobs = []
        self.batchsize = batchsize
        self.min_progress = min_progress
        self.max_progress = max_progress

    def __str__(self):
        return "BatchJobRunner (%s)" % self.basejob

    def add_job(self, job):
        self.jobs.append(job)

    def run(self):
        class JobList:
            def __init__(self, jobs):
                self.jobs = jobs
                self.index = 0
                self.count = len(jobs)

            def __nonzero__(self):
                return self.index < self.count

            def next(self):
                if self.index < self.count:
                    job = self.jobs[self.index]
                    self.index = self.index + 1
                    return job
                return None

        joblist = JobList(self.jobs)
        done_count = 0
        batch = []

        logger.info("%s: %d total jobs" % (self, joblist.count))

        while joblist and len(batch) < self.batchsize:
            job = joblist.next()
            batch.append(job)
            job.start()
            logger.debug("%s: starting batch job #%d (%s)"
                         % (self, joblist.index, job))

        # iterate until both jobs and batch are empty
        while joblist or batch:
            # check jobs in the batch
            rebuild_batch = False
            batch_progress = 0.0
            something_done = False
            for i, job in enumerate(batch):
                job.refresh()
                if job.done():
                    something_done = True
                    done_count = done_count + 1
                    if joblist:
                        batch[i] = joblist.next()
                        batch[i].start()
                        logger.debug("%s: starting batch job #%d (%s)"
                                     % (self, joblist.index, batch[i]))
                    else:
                        batch[i] = None
                        rebuild_batch = True
                else:
                    batch_progress = batch_progress + float(job.progress)

            total_progress = (float(done_count * 100) + batch_progress) / joblist.count
            job_progress = (float(self.min_progress) +
                            ((total_progress / 100.0) *
                             (self.max_progress - self.min_progress)))
            #logger.debug(
            #    "%s: progress %d%% (basejob %d%%) (%d/%d done, %d in batch)" %
            #    (self, int(total_progress), int(job_progress),
            #    done_count, joblist.count, len(batch)))
            self.basejob.mark_progress(job_progress)

            if not something_done:
                time.sleep(0.2)

            elif rebuild_batch:
                batch = [j for j in batch if j is not None]

        return

        for i in range(0, len(jobs), self.batchsize):
            batch = jobs[i:i+self.batchsize]
            batch_status = {}
            for j, job in enumerate(batch):
                batch_status[job.id] = False
                logger.debug("%s: starting job #%d (%s)"
                             % (self, j + i, job))
                job.start()

            interval = 0.2
            max_interval = 2
            batch_done = False
            while not batch_done:
                batch_progress = 0
                batch_done = True
                for job in batch:
                    job.refresh()

                    if batch_status[job.id] is False:
                        if job.done():
                            batch_status[job.id] = True
                        else:
                            batch_done = False
                            batch_progress += (float(job.progress) /
                                               float(self.batchsize))
                    else:
                        batch_progress += (100.0 / float(self.batchsize))

                total_progress = (i * 100.0 + batch_progress * self.batchsize) / len(jobs)
                job_progress = (self.min_progress +
                                (total_progress * (self.max_progress -
                                                   self.min_progress)) / 100)
                logger.debug("%s: batch[%d:%d] %d%% / total %d%% / job %d%%",
                             self, i, i+self.batchsize, int(batch_progress),
                             int(total_progress), int(job_progress))
                self.basejob.mark_progress(job_progress)
                if not batch_done:
                    time.sleep(interval)
                    #interval = (interval * 2) if interval < max_interval else max_interval
