# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import copy
import string
import inspect
import logging
import datetime
import tokenize
import importlib
from StringIO import StringIO

import pytz

from django.db import models
from django.db import DatabaseError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify

from steelscript.common.datastructures import JsonDict
from steelscript.common.datastructures import DictObject
from steelscript.common.timeutils import timedelta_total_seconds
from steelscript.appfwk.project.utils import (get_module_name, get_sourcefile,
                                              get_namespace)
from steelscript.appfwk.libs.fields import (PickledObjectField, FunctionField,
                                            SeparatedValuesField,
                                            check_field_choice,
                                            field_choice_str)
from steelscript.appfwk.apps.datasource.exceptions import \
    TableComputeSyntheticError, DatasourceException


logger = logging.getLogger(__name__)


# Load Synthetic modules - they may be referenced by
# string name in synthetic columns
for module in settings.APPFWK_SYNTHETIC_MODULES:
    logger.info("Importing synthetic module: %s" % module)
    globals()[module] = importlib.import_module(module)


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

    :param parents: List of parent keywords that this field depends on
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

    # Table data is produced by a queryclassname defined within the
    # named module
    module = models.CharField(max_length=200)
    queryclassname = models.CharField(max_length=200)

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
    fields = models.ManyToManyField(TableField)

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
                msg = 'Invalid table ref as dict, expected namespace/name'
                raise KeyError(msg)
            return arg

        if isinstance(arg, Table):
            table = arg
        elif hasattr(arg, 'table'):
            # Datasource table
            table = arg.table
        elif isinstance(arg, int):
            table = Table.objects.get(id=arg)
        else:
            raise ValueError('No way to handle Table arg of type %s'
                             % type(arg))
        return {'sourcefile': table.sourcefile,
                'namespace': table.namespace,
                'name': table.name}

    @classmethod
    def from_ref(cls, ref):
        try:
            return Table.objects.get(sourcefile=ref['sourcefile'],
                                     namespace=ref['namespace'],
                                     name=ref['name'])
        except ObjectDoesNotExist:
            logger.exception('Failed to resolve table ref: %s/%s/%s' %
                             (ref['sourcefile'], ref['namespace'],
                              ref['name']))
            raise

    def __unicode__(self):
        return "<Table %s (%s)>" % (str(self.id), self.name)

    def __repr__(self):
        return unicode(self)

    @property
    def queryclass(self):
        # Lookup the query class for the table associated with this task
        try:
            i = importlib.import_module(self.module)
            queryclass = i.__dict__[self.queryclassname]
        except:
            raise DatasourceException(
                "Could not lookup queryclass %s in module %s" %
                (self.queryclassname, self.module))

        return queryclass

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
        for c in Column.objects.filter(table=self).order_by('position',
                                                            'name'):
            if synthetic is not None and c.synthetic != synthetic:
                continue
            if c.ephemeral is not None and c.ephemeral != ephemeral:
                continue
            if iskey is not None and c.iskey != iskey:
                continue
            filtered.append(c)

        return filtered

    def copy_columns(self, table, columns=None, except_columns=None,
                     synthetic=None, ephemeral=None):
        """ Copy the columns from `table` into this table.

        This method will copy all the columns from another table, including
        all attributes as well as sorting.

        """

        if not isinstance(table, Table):
            table = Table.from_ref(table)

        sortcols = []
        sortdir = []
        for c in table.get_columns(synthetic=synthetic, ephemeral=ephemeral):
            if columns is not None and c.name not in columns:
                continue
            if except_columns is not None and c.name in except_columns:
                continue

            if table.sortcols and (c.name in table.sortcols):
                sortcols.append(c.name)
                sortdir.append(table.sortdir[table.sortcols.index(c.name)])

            c.pk = None
            c.table = self

            c.save()

            # Allocate an id, use that as the position
            c.position = c.id
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

            2. If the table is a time-based table with a defined resolution,
               the result is resampled.

            3. Any remaining columns are computed.
        """
        if df is None:
            return None

        all_columns = job.get_columns()
        all_col_names = [c.name for c in all_columns]

        def compute(df, syncols):
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
                        elif tvalue in all_col_names:
                            newexpr += "df['%s']" % tvalue
                        elif tvalue in job.criteria:
                            newexpr += '"%s"' % str(job.criteria.get(tvalue))
                        else:
                            raise ValueError("Invalid variable name: %s" % tvalue)

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
                    newexpr += ' '
                try:
                    df[syncol.name] = eval(newexpr)
                except NameError as e:
                    m = (('%s: expression failed: %s, check '
                          'APPFWK_SYNTHETIC_MODULES: %s') %
                         (self, newexpr, str(e)))
                    logger.exception(m)
                    raise TableComputeSyntheticError(m)

        # 1. Compute synthetic columns where post_resample is False
        compute(df, [col for col in all_columns if
                     (col.synthetic and col.compute_post_resample is False)])

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
                       ("%s: 'resample' is set but no 'time' column'" %
                        self))

            if (('resolution' not in job.criteria) and
                    ('resample_resolution' not in job.criteria)):
                raise (TableComputeSyntheticError
                       (("%s: 'resample' is set but criteria missing " +
                         "'resolution' or 'resample_resolution'") % self))

            how = {}
            for k in df.keys():
                if k == timecol or k not in colmap:
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

        # Table property '_query_class' may be either a string name
        # or an actual class reference.  Convert to string name for storage
        queryclassname = cls._query_class
        if inspect.isclass(queryclassname):
            queryclassname = queryclassname.__name__

        sourcefile = table_kwargs.get('sourcefile',
                                      get_sourcefile(get_module_name()))
        namespace = table_kwargs.get('namespace',
                                     get_namespace(sourcefile))

        if len(Table.objects.filter(name=name,
                                    namespace=namespace,
                                    sourcefile=sourcefile)) > 0:
            msg = ("Table '%s' already exists in namespace '%s' "
                   "(sourcefile '%s')") % (name, namespace, sourcefile)
            raise ValueError(msg)

        table_kwargs['namespace'] = namespace
        table_kwargs['sourcefile'] = sourcefile

        logger.debug('Creating table %s' % name)
        t = cls(name=name, module=cls.__module__,
                queryclassname=queryclassname, options=options, **table_kwargs)
        try:
            t.save()
        except DatabaseError as e:
            if 'no such table' in str(e):
                msg = str(e) + ' -- did you forget class Meta: proxy=True?'
                raise DatabaseError(msg)
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
            * date

        :param enum units: Units for data in this column, defaults to none:

            * none - no units
            * s - seconds
            * ms - milliseconds
            * B - bytes
            * B/s - bytes per second
            * b - bits
            * b/s - bits per second
            * pct - percentage

        :param int position: Display position relative to other columns,
            automatically computed by default

        :param bool synthetic: Set True to compute this columns value
            according to ``compute_expression``

        :param str compute_expression: Computation expression for syntetic
            columns

        :param bool compute_post_resample: If true, compute this synthetic
            column after resampling (time series only)

        :param str resample_operation: Operation to use on this column to
            aggregate multiple rows during resampling, defaults to sum


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


class DatasourceQuery(object):
    def __init__(self, job):
        self.job = job
        self.table = self.job.table

    def __unicode__(self):
        return "<%s %s>" % (self.__class__.__name__, self.job)

    def __str__(self):
        return "<%s %s>" % (self.__class__.__name__, self.job)

    def run(self):
        return True

    def post_run(self):
        return True

    def _post_query_continue(self, jobids, callback):
        jobs = {}
        # Hack to avoid circular import problem
        Job = self.job.__class__
        for name, jobid in jobids.iteritems():
            jobs[name] = Job.objects.get(id=jobid)

        return callback(self, jobs)

# Backward compatibility
TableQueryBase = DatasourceQuery


class Column(models.Model):

    table = models.ForeignKey(Table)
    name = models.CharField(max_length=300)
    label = models.CharField(max_length=300, null=True)
    position = models.IntegerField(default=1)
    options = PickledObjectField()

    iskey = models.BooleanField(default=False)

    synthetic = models.BooleanField(default=False)

    # Ephemeral columns are columns added to a table at run-time
    ephemeral = models.ForeignKey('jobs.Job', null=True)

    compute_post_resample = models.BooleanField(default=False)
    compute_expression = models.CharField(max_length=300)
    resample_operation = models.CharField(max_length=300, default='sum')

    DATATYPE_FLOAT = 0
    DATATYPE_INTEGER = 1
    DATATYPE_TIME = 2
    DATATYPE_STRING = 3
    DATATYPE_HTML = 4
    DATATYPE_DATE = 5

    datatype = models.IntegerField(
        default=DATATYPE_FLOAT,
        choices=((DATATYPE_FLOAT, "float"),
                 (DATATYPE_INTEGER, "integer"),
                 (DATATYPE_TIME, "time"),
                 (DATATYPE_STRING, "string"),
                 (DATATYPE_HTML, "html"),
                 (DATATYPE_DATE, "date"))
    )

    UNITS_NONE = 0
    UNITS_SECS = 1
    UNITS_MSECS = 2
    UNITS_BYTES = 3
    UNITS_BYTES_PER_SEC = 4
    UNITS_PCT = 5
    UNITS_BITS = 6
    UNITS_BITS_PER_SEC = 7
    units = models.IntegerField(
        default=UNITS_NONE,
        choices=((UNITS_NONE, "none"),
                 (UNITS_SECS, "s"),
                 (UNITS_MSECS, "ms"),
                 (UNITS_BYTES, "B"),
                 (UNITS_BYTES_PER_SEC, "B/s"),
                 (UNITS_PCT, "pct"),
                 (UNITS_BITS, "b"),
                 (UNITS_BITS_PER_SEC, "b/s"),
                 )
    )

    formatter = models.TextField(null=True, blank=True)

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
    def create(cls, table, name, label=None,
               datatype=DATATYPE_FLOAT, units=UNITS_NONE,
               iskey=False, position=None, **kwargs):

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

        try:
            c.save()
        except DatabaseError as e:
            if 'no such table' in str(e):
                msg = str(e) + ' -- did you forget class Meta: proxy=True?'
                raise DatabaseError(msg)
            raise

        c.position = position or c.id
        c.save()

        return c

    def isnumeric(self):
        return self.datatype in [self.DATATYPE_FLOAT, self.DATATYPE_INTEGER]

    def istime(self):
        return self.datatype == self.DATATYPE_TIME

    def isdate(self):
        return self.datatype == self.DATATYPE_DATE

    def units_str(self):
        if self.units == self.UNITS_NONE:
            return None
        return field_choice_str(self, 'units', self.units)


class Criteria(DictObject):
    """ Manage a collection of criteria values. """

    def __init__(self, **kwargs):
        """ Initialize a criteria object based on key/value pairs. """

        self.ignore_cache = False

        self.starttime = None
        self.endtime = None
        self.duration = None

        super(Criteria, self).__init__(kwargs)

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
        # else:
        #    param = TableField.find_instance(key)
        #    if param.initial != value:
        #        param.initial = value
        #        param.save()

    @classmethod
    def is_timeframe_key(cls, key):
        return (key in ['starttime', 'endtime', 'duration',
                        '_orig_starttime', '_orig_endtime', '_orig_duration'])

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
            rev_field_map[v] = k

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

        logger.debug("compute_times: start %s(%s), end %s(%s), duration %s(%s)"
                     % (starttime, type(starttime), endtime, type(endtime),
                        duration, type(duration)))

        if starttime is not None:
            if endtime is not None:
                duration = endtime - starttime
            elif duration is not None:
                endtime = starttime + duration
            else:
                msg = ("Cannot compute times, have starttime but not "
                       "endtime or duration")
                logger.debug(msg)
                raise ValueError(msg)

        elif endtime is None:
            endtime = datetime.datetime.now(pytz.UTC)

        if duration is not None and (isinstance(duration, datetime.datetime) or
                                     isinstance(duration, datetime.timedelta)):
            starttime = endtime - duration
        else:
            msg = ("Cannot compute times, have endtime but not "
                   "starttime or duration")
            logger.debug(msg)
            raise ValueError(msg)

        self.duration = duration
        self.starttime = starttime
        self.endtime = endtime
