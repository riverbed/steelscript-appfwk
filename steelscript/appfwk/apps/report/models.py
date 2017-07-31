# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import re
import logging
from datetime import datetime
from collections import OrderedDict

from django.conf import settings
from django.db import models
from django.db.models import Max, Sum
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from model_utils.managers import InheritanceManager
from steelscript.appfwk.apps.jobs.models import Job

from steelscript.common.datastructures import JsonDict
from steelscript.appfwk.project.utils import (get_module, get_module_name,
                                              get_sourcefile, get_namespace)
from steelscript.appfwk.apps.datasource.models import Table, TableField
from steelscript.appfwk.libs.fields import \
    PickledObjectField, SeparatedValuesField
from steelscript.appfwk.apps.preferences.models import AppfwkUser
from steelscript.appfwk.apps.jobs.models import TransactionLock

from steelscript.appfwk.apps.alerting.models import (post_data_save,
                                                     error_signal)

logger = logging.getLogger(__name__)


class WidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None,
                'axes': None}


class Report(models.Model):
    """ Defines a Report as a collection of Sections and their Widgets. """
    title = models.CharField(max_length=200)
    description = models.TextField(null=True)
    position = models.DecimalField(max_digits=7, decimal_places=3, default=10)
    enabled = models.BooleanField(default=True)

    slug = models.SlugField(unique=True, max_length=100)
    namespace = models.CharField(max_length=100)
    sourcefile = models.CharField(max_length=200)
    filepath = models.FilePathField(max_length=200, path=settings.REPORTS_DIR)

    fields = models.ManyToManyField(TableField, blank=True)
    field_order = SeparatedValuesField(null=True,
                                       default=['starttime', 'endtime',
                                                'duration', 'filterexpr'],
                                       blank=True)
    hidden_fields = SeparatedValuesField(null=True, blank=True)

    # create an 'auto-load'-type report which uses default criteria
    # values only, and optionally set a refresh timer
    hide_criteria = models.BooleanField(default=False)
    reload_minutes = models.IntegerField(default=0)     # 0 means no reloads
    reload_offset = models.IntegerField(default=15*60)  # secs, default 15 min
    auto_run = models.BooleanField(default=False)
    static = models.BooleanField(default=False)

    @classmethod
    def create(cls, title, **kwargs):
        """Create a new Report object and save it to the database.

        :param str title: Title for the report

        :param float position: Position in the menu for this report.
            By default, all system reports have a ``position`` of 9 or
            greater.

        :param list field_order: List declaring the order to display
            criteria fields.  Any fields not list are displayed after
            all listed fields.

        :param list hidden_fields: List of criteria fields to hide from UI

        :param bool hide_criteria: Set to true to hide criteria and run on load
        :param int reload_minutes: If non-zero, report will be reloaded
            automatically at the given duration in minutes
        :param bool reload_offset: In seconds, the amount of time to consider
            a reload interval to have passed.  This avoids waiting until
            half of the reload interval before turning over to next interval.
            This also affects how the report gets reloaded in the browser,
            if this offset value is smaller than the interval, it will be used
            to delay the report reloads.
            For example, given ``reload_minutes`` of ``1`` and
            ``reload_offset`` of ``10``, the browser will reload all the
            widgets every minute at 10 seconds past the minute.

        :param bool auto_run: Set to true to run report automatically.  This
            will only run the report once, versus the reload options which
            setup continuous report reloads.

        :param bool static: Set to true to read data from WidgetDataCache.
            To populate WidgetDataCache for static reports, run the report by
            setting live=True in url.

        """

        logger.debug('Creating report %s' % title)
        r = cls(title=title, **kwargs)
        r.save()
        return r

    def __init__(self, *args, **kwargs):
        super(Report, self).__init__(*args, **kwargs)
        self._sections = []

    def save(self, *args, **kwargs):
        """ Apply sourcefile and namespaces to newly created Reports.

        sourcefiles will be parsed into the following namespaces:
        'config.reports.1_overall' --> 'default'
        'steelscript.netshark.appfwk.reports.3_shark' --> 'netshark'
        'steelscript.appfwk.business_hours.reports.x_rpt' --> 'business_hours'
        """
        if not self.sourcefile:
            mod = get_module()
            self.filepath = mod.__file__
            modname = get_module_name(mod)
            self.sourcefile = get_sourcefile(modname)

        if not self.namespace:
            self.namespace = get_namespace(self.sourcefile)

        if not self.slug:
            self.slug = slugify(self.sourcefile.split('.')[-1])

        super(Report, self).save(*args, **kwargs)

    def __unicode__(self):
        return "<Report %s (%s)>" % (self.title, self.id)

    def __repr__(self):
        return unicode(self)

    def add_section(self, title=None, **kwargs):
        """Create a new section associated with this report.

        :param str title: Title for the section.  Defaults to
            ``section<n>``.

        See :py:meth:`Section.create` for a complete description
        and a list of valid ``kwargs``.

        """
        if title is None:
            title = 'section%d' % len(self._sections)
        s = Section.create(report=self, title=title, **kwargs)
        self._sections.append(s)
        return s

    def add_widget(self, cls, table, title, **kwargs):
        """Create a new widget associated with the last section added.

        :param cls: UI class that will be used to render this widget
        :param table: Table providing data for this widget
        :param str title: Display title for this widget

        See the specific ``cls.create()`` method for additional kwargs.

        """

        if len(self._sections) == 0:
            raise ValueError('Widgets can only be added to Sections. '
                             'Add section using "add_section" method first.')
        s = kwargs.pop('section', self._sections[-1])
        return cls.create(s, table, title, **kwargs)

    def collect_fields_by_section(self):
        """ Return a dict of all fields related to this report by section id.
        """

        # map of section id to field dict
        fields_by_section = OrderedDict()

        # section id=0 is the "common" section
        # fields attached directly to the Report object are always added
        # to the common section
        fields_by_section[0] = OrderedDict()
        if self.fields:
            report_fields = {}
            for f in self.fields.all():
                report_fields[f.keyword] = f

            fields_by_section[0].update(report_fields)

        # Pull in fields from each section (which may add fields to
        # the common as well)
        for s in Section.objects.filter(report=self):
            for secid, fields in s.collect_fields_by_section().iteritems():
                if secid not in fields_by_section:
                    fields_by_section[secid] = fields
                else:
                    # update fields from fields_by_section so that the
                    # first definition of a field takes precedence.
                    # For example, if 'start' is defined at the report
                    # 'common' level, it's field will be used rather
                    # than that defined in the section.  This is useful
                    # for custimizing the appearance/label/defaults of
                    # fields pulled in from tables
                    fields.update(fields_by_section[secid])
                    fields_by_section[secid] = fields

        # Reorder fields in each section according to the field_order list
        new_fields_by_section = {}
        for i, fields in fields_by_section.iteritems():
            # collect all field names
            section_fields = fields_by_section[i]
            section_field_names = set(section_fields.keys())

            ordered_field_names = OrderedDict()
            # Iterate over the defined order list, which may not
            # address all fields
            for name in (self.field_order or []):
                if name in section_field_names:
                    ordered_field_names[name] = section_fields[name]
                    section_field_names.remove(name)

            # Preserve the order of any fields left
            for name in section_field_names:
                ordered_field_names[name] = section_fields[name]

            new_fields_by_section[i] = ordered_field_names

        return new_fields_by_section

    def widgets(self):
        return Widget.objects.filter(
            section__in=Section.objects.filter(report=self)).order_by('id')

    def tables(self, order_by='id'):
        """Return all tables from this report, ordered by `order_by`."""
        return (Table.objects.filter(
                widget__in=Widget.objects.filter(
                    section__in=Section.objects.filter(
                        report=self)))
                .distinct().order_by(order_by))

    def widget_definitions(self, criteria):
        """Return list of widget definitions suitable for a JSON response.
        """
        definitions = []

        # Add 'id' to order by so that stacked widgets will
        # return with the same order as created
        for w in self.widgets().order_by('row', 'col', 'id'):
            widget_def = w.get_definition(criteria)
            definitions.append(widget_def)

        return definitions


class ReportStatus(object):
    NEW = 0
    RUNNING = 1
    COMPLETE = 2
    ERROR = 3


class ReportHistory(models.Model):
    """ Define a record history of running report."""
    namespace = models.CharField(max_length=50)
    slug = models.CharField(max_length=50)
    bookmark = models.CharField(max_length=400)
    first_run = models.DateTimeField()
    last_run = models.DateTimeField()
    job_handles = models.TextField()
    user = models.CharField(max_length=50)
    criteria = PickledObjectField()
    run_count = models.IntegerField()

    status_choices = ((ReportStatus.NEW, "New"),
                      (ReportStatus.RUNNING, "Running"),
                      (ReportStatus.COMPLETE, "Complete"),
                      (ReportStatus.ERROR, "Error"))

    status = models.IntegerField(
        default=ReportStatus.NEW,
        choices=status_choices)

    @classmethod
    def create(cls, **kwargs):
        """ Create a new report history object and save it to database.
        :param str namespace: name of one set of report slugs
        :param str slug: the slug of the report
        :param str bookmark: the bookmark link of the report
        :param datetime last_run: Time when the report with the same criteria
          ran at the first time
        :param datetime last_run: Time when the report with the same criteria
          ran last time
        :param str job_handles: comma separated job handle strings of the
          report
        :param str user: name of the user who ran the report
        :param dict criteria: criteria fields that the report is running with
        :param int run_count: the number of times the report has run with the
          same criteria
        :return: the created report history object
        """
        job_handles = kwargs.get('job_handles')
        try:
            rh_obj = cls.objects.get(job_handles=job_handles)
        except ObjectDoesNotExist:
            rh_obj = cls(**kwargs)
            rh_obj.save()
        else:
            with TransactionLock(rh_obj, '%s_create' % rh_obj):
                rh_obj.status = ReportStatus.NEW
                rh_obj.last_run = kwargs.get('last_run')
                rh_obj.run_count += 1
                rh_obj.save()
        finally:
            return

    def __unicode__(self):
        return ("<Report History %s %s/%s>"
                % (self.id, self.namespace, self.slug))

    def __repr__(self):
        return unicode(self)

    def update_status(self, status):
        if self.status != status:
            with TransactionLock(self, '%s.update_status' % self):
                self.status = status
                self.save()

    def format_ts(self, ts):
        ltime = timezone.localtime(ts)
        return ltime.strftime("%Y/%m/%d %H:%M:%S")

    @property
    def format_last_run(self):
        return self.format_ts(self.last_run)

    @property
    def format_first_run(self):
        return self.format_ts(self.first_run)

    @property
    def status_name(self):
        return self.status_choices[self.status][1]

    @property
    def criteria_html(self):
        # length of business_hours_weekends.
        # current longest field
        tr_line = '<tr><td><b>{0}</b>:&nbsp;</td><td>{1}</td></tr>'
        cprops = self.criteria.keys()
        cprops.sort()
        rstr = '<table>'
        for k in cprops:
            rstr += tr_line.format(k,
                                   self.criteria[k])
        rstr += '</table>'
        # logger.debug("criteria_html: {0}".format(rstr))
        return rstr


@receiver(post_data_save, dispatch_uid='job_complete_receiver')
def update_report_history_status_on_complete(sender, **kwargs):
    """ Update the status of the report history that shares the same job handle
    with the just completed job.

    If one widget job's status is ERROR, then update the status of the report
    history as ERROR; if one report job's status is running, then update the
    status of the report history as RUNNING; if all jobs' status are COMPLETE,
    then update the status of the report history as COMPLETE.

    :param sender: job object that just completed
    """
    if not settings.REPORT_HISTORY_ENABLED:
        return

    rhs = ReportHistory.objects.filter(
        job_handles__contains=sender.handle).exclude(
        status__in=[ReportStatus.ERROR, ReportStatus.COMPLETE])

    logger.debug('Report history objects found with Sender handle %s: %s' %
                 (sender.handle, rhs))

    for rh in rhs:
        jobs = Job.objects.filter(handle__in=rh.job_handles.split(','))

        logger.debug('Jobs found for ReportHistory %s: %s' % (rh, jobs))

        if any([job.status == Job.ERROR for job in jobs]):
            logger.debug('Updating status of ReportHistory %s to ERROR' % rh)
            rh.update_status(ReportStatus.ERROR)

        elif any([job.status == Job.RUNNING for job in jobs]):
            logger.debug('Updating status of ReportHistory %s to RUNNING' % rh)
            rh.update_status(ReportStatus.RUNNING)

        elif jobs and all([job.status == Job.COMPLETE for job in jobs]):
            logger.debug('Updating status of ReportHistory %s to COMPLETE' % rh)
            rh.update_status(ReportStatus.COMPLETE)


@receiver(error_signal, dispatch_uid='job_error_receiver')
def update_report_history_status_on_error(sender, **kwargs):
    """ Set Error status for the report history that shares the same job handle
    with the just erred job.

    :param sender: job object that just erred
    """
    if not settings.REPORT_HISTORY_ENABLED:
        return

    rhs = ReportHistory.objects.filter(
        job_handles__contains=sender.handle).exclude(
        status__in=[ReportStatus.ERROR, ReportStatus.COMPLETE])

    for rh in rhs:
        logger.debug('Updating status of ReportHistory %s to ERROR' % rh)
        rh.update_status(ReportStatus.ERROR)


class Section(models.Model):
    """ Define a section of a report.

    Sections provide a means to control how fields and criteria are
    handled.  The criteria is a Criteria object filled in with values
    provided by the end user based on a set of TableFields.

    All tables (via Widgets) in the same section will all be passed
    the same run-time criteria.  The set of fields that a user may
    fill in for a section is a union of all TableFields of all tables
    in that section.  The union is based on the TableField keyword
    attribute, thus two tables that each define a TableField with the
    same keyword will share the same value in the resulting criteria
    object at run time.  The first TableField instance found for a
    given keyword is the actual object instance used for generating
    the UI form.

    If there are multiple sections, the section may be configured to
    either inherit fields from the report (SectionFieldMode.INHERIT)
    or to make the field specific to the section
    (SectionFieldMode.SECTION).

    Each section has a default mode that applies to all field
    keywords that are not called out explicitly.  If the section
    default mode is INHERIT, specific keywords can be set to SECTION
    by creating SectionFieldMode entries.

    """

    report = models.ForeignKey(Report)
    title = models.CharField(max_length=200, blank=True)
    position = models.DecimalField(max_digits=7, decimal_places=3, default=10)
    fields = models.ManyToManyField(TableField)

    def __unicode__(self):
        return '<Section %s (%s)>' % (self.title, self.id)

    def __repr__(self):
        return unicode(self)

    @classmethod
    def create(cls, report, title='', position=None,
               section_keywords=None,
               default_field_mode=None,
               keyword_field_modes=None):
        """ Create a Section of a report and define field modes.

        :param report: the report this section applies to

        :param str title: section title to display

        :param float position: relative position for ordering on display,
            if None (default), this will be added as the last
            section of the current report

        :param default_field_mode: the default mode for how to
            handle fields.  If None (default), ``INHERIT`` will be used

        :param keyword_field_modes: dict of keyword to mode to
            override the ``default_field_mode``.  Each entry in this
            dict will result in a SectionFieldMode object

        """
        if position is None:
            posmax = (Section.objects
                      .filter(report=report)
                      .aggregate(Max('position')))
            position = (posmax['position__max'] or 0) + 1

        section = Section(report=report, title=title, position=position)
        section.save()

        critmode = SectionFieldMode(
            section=section,
            keyword='',
            mode=default_field_mode or SectionFieldMode.INHERIT
        )
        critmode.save()

        if section_keywords is not None:
            if not isinstance(section_keywords, list):
                section_keywords = [section_keywords]

            for keyword in section_keywords:
                critmode = SectionFieldMode(section=section,
                                            keyword=keyword,
                                            mode=SectionFieldMode.SECTION)
                critmode.save()

        if keyword_field_modes:
            for keyword, mode in keyword_field_modes.iteritems():
                critmode = SectionFieldMode(section=section,
                                            keyword=keyword,
                                            mode=mode)
                critmode.save()

        return section

    def add_widget(self, cls, table, title, **kwargs):
        """Create a new widget associated with this section

        :param cls: UI class that will be used to render this widget
        :param table: Table providing data for this widget
        :param str title: Display title for this widget

        See the specific ``cls.create()`` method for additional kwargs.

        """
        return cls.create(self, table, title, **kwargs)

    def collect_fields_by_section(self):
        # Gather up all fields
        fields = []

        # All fields attached to the section
        for f in self.fields.all().order_by('id'):
            fields.append(f)

        # All fields attached to any Widget's Tables
        for w in Widget.objects.filter(section=self):
            for t in w.tables.all():
                for f in t.fields.all().order_by('id'):
                    fields.append(f)

        fields_by_section = OrderedDict()
        fields_by_section[0] = {}
        fields_by_section[self.id] = {}
        for f in fields:
            # Split fields into section vs common based on the field_mode
            # for each keyword
            if self.fields_mode(f.keyword) is SectionFieldMode.SECTION:
                # Section fields are prefixed with the section id
                # in the field map
                section_id = self.id
            else:
                section_id = 0

            key = f.keyword
            if key not in fields_by_section[section_id]:
                fields_by_section[section_id][key] = f

        return fields_by_section

    def fields_mode(self, keyword):
        try:
            m = self.sectionfieldmode_set.get(keyword=keyword)
            return m.mode
        except ObjectDoesNotExist:
            pass

        try:
            m = self.sectionfieldmode_set.get(keyword='')
            return m.mode
        except ObjectDoesNotExist:
            pass

        return SectionFieldMode.INHERIT


class SectionFieldMode(models.Model):
    section = models.ForeignKey(Section)
    keyword = models.CharField(blank=True, max_length=200)

    INHERIT = 0
    SECTION = 1
    mode = models.IntegerField(default=INHERIT,
                               choices=((INHERIT, "Inherit"),
                                        (SECTION, "Section")))


class Widget(models.Model):
    """ Defines a UI widget and the source datatables
    """
    tables = models.ManyToManyField(Table)
    section = models.ForeignKey(Section)
    title = models.CharField(max_length=100)
    row = models.IntegerField()
    col = models.IntegerField()
    width = models.IntegerField(default=6)

    # setting height of 0 will let widget box auto-size to resulting data
    height = models.IntegerField(default=300)
    rows = models.IntegerField(default=-1)
    options = PickledObjectField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = PickledObjectField()

    # not globally unique, but should be sufficiently unique within a report
    slug = models.SlugField(max_length=100)

    # widget to be stacked below the previous widget on the same row
    stack_widget = models.BooleanField(default=False)

    objects = InheritanceManager()

    def __repr__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def __unicode__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def save(self, *args, **kwargs):
        self.slug = '%s-%d-%d' % (slugify(self.title), self.row, self.col)
        super(Widget, self).save(*args, **kwargs)

    @classmethod
    def create(cls, *args, **kwargs):
        options = kwargs.pop('options', None)
        table = kwargs.pop('table', None)

        w = Widget(*args, **kwargs)
        w.compute_row_col()

        if options:
            w.options = JsonDict(options)

        w.save()

        if table:
            w.tables.add(table)

        return w

    def get_definition(self, criteria):
        """Get dict of widget attributes for sending via JSON."""
        report = self.section.report

        widget_def = {
            "widgettype": self.widgettype().split("."),
            "posturl": reverse('widget-job-list',
                               args=(report.namespace,
                                     report.slug,
                                     self.slug)),
            "updateurl": reverse('widget-criteria',
                                 args=(report.namespace,
                                       report.slug,
                                       self.slug)),
            "options": self.uioptions,
            "widgetid": self.id,
            "widgetslug": self.slug,
            "row": self.row,
            "width": self.width,
            "height": self.height,
            "criteria": criteria,
        }

        return widget_def

    def widgettype(self):
        return '%s.%s' % (self.module.split('.')[-1], self.uiwidget)

    def table(self, i=0):
        return self.tables.all()[i]

    def compute_row_col(self):
        rowmax = self.section.report.widgets().aggregate(Max('row'))
        row = rowmax['row__max']
        if row is None:
            row = 1
            col = 1
        elif self.stack_widget:
            # This widget needs to be stacked below the previous widget
            pre_w = self.section.report.widgets().order_by('-row', '-col')[0]
            if pre_w.width != self.width:
                raise ValueError("The stack widget with title '%s' should set "
                                 "with width %s." % (self.title, pre_w.width))
            elif pre_w.title.lower() == self.title.lower():
                raise ValueError("The stack widget title '%s' is the same as "
                                 "the previous widget, thus should be "
                                 "changed." % self.title)
            row = pre_w.row
            col = pre_w.col
        else:
            widthsum = (self.section
                        .report.widgets()
                        .filter(row=row)
                        .aggregate(Sum('width')))
            width = widthsum['width__sum']
            if width + self.width > 12:
                row += 1
                col = 1
            else:
                col = width + 1

        self.row = row
        self.col = col

    def collect_fields(self):
        # Gather up all fields
        fields = OrderedDict()

        # All fields attached to the section's report
        for f in self.section.report.fields.all().order_by('id'):
            fields[f.keyword] = f

        # All fields attached to the section
        for f in self.section.fields.all().order_by('id'):
            if f.keyword not in fields:
                fields[f.keyword] = f

        # All fields attached to any Widget's Tables
        for w in self.section.widget_set.all().order_by('id'):
            for t in w.tables.all():
                for f in t.fields.all().order_by('id'):
                    if f.keyword not in fields:
                        fields[f.keyword] = f

        return fields


class WidgetDataCache(models.Model):
    """
    Defines a cache of widget data for a static report. The primary key is
    defined as <report_slug><widget_slug>
    """
    report_widget_id = models.CharField(max_length=500, primary_key=True)
    data = models.TextField(blank=False)
    created = models.DateTimeField()

    def __unicode__(self):
        return "<WidgetDataCache %s/%s/%s>" % (self.id,
                                               self.report_widget_id[:10],
                                               self.created)

    def save(self, *args, **kwargs):
        """ On save, update created timestamp """
        self.created = datetime.utcnow()
        return super(WidgetDataCache, self).save(*args, **kwargs)


class WidgetJob(models.Model):
    """ Query point for status of Jobs for each Widget.
    """
    widget = models.ForeignKey(Widget)
    job = models.ForeignKey(Job)

    def __unicode__(self):
        return "<WidgetJob %s: widget %s, job %s>" % (self.id,
                                                      self.widget.id,
                                                      self.job.id)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.job.reference(str(self))
            super(WidgetJob, self).save(*args, **kwargs)


class WidgetAuthToken(models.Model):
    """ Authentication token for each user per widget per report """

    token = models.CharField(max_length=200)
    user = models.ForeignKey(AppfwkUser)
    pre_url = models.CharField(max_length=200, verbose_name='URL')
    criteria = PickledObjectField()
    edit_fields = SeparatedValuesField(null=True)
    touched = models.DateTimeField(auto_now=True,
                                   verbose_name='Last Time used')

    def __unicode__(self):
        return ("<Token %s, User %s, pre_url %s>" %
                (self.token, self.user, self.pre_url))


@receiver(pre_delete, sender=WidgetJob)
def _widgetjob_delete(sender, instance, **kwargs):
    try:
        instance.job.dereference(str(instance))
    except ObjectDoesNotExist:
        logger.info('Job not found for instance %s, ignoring.' % instance)


class UIWidgetHelper(object):
    """Helper class for ui-module widget classes to use."""

    def __init__(self, widget, job):
        self.widget = widget
        self.job = job

        # properties
        self._colmap = None
        self._all_cols = None
        self._keycols = None
        self._valcols = None

    @staticmethod
    def clean_key(s):
        # remove unwanted characters from string `s`
        return re.sub('[:. ]', '_', s)

    class ColInfo:
        def __init__(self, col, dataindex, axis, fmt=None, allow_html=False):
            self.col = col
            self.key = UIWidgetHelper.clean_key(col.name)
            self.label = col.label
            self.dataindex = dataindex
            self.axis = axis
            self.formatter = fmt
            self.allow_html = allow_html
            self.sortable = True
            self.istime = col.istime()
            self.isdate = col.isdate()

        def to_json(self, *keys):
            # return a dict object with just the requested keys
            return {k: getattr(self, k) for k in keys}

    @property
    def all_cols(self):
        if self._all_cols:
            return self._all_cols

        self._all_cols = self.job.get_columns()
        return self._all_cols

    @property
    def col_names(self):
        return [c.name for c in self.all_cols]

    @property
    def keycols(self):
        if self._keycols:
            return self._keycols

        kcols = getattr(self.widget.options, 'keycols', None)
        if kcols:
            self._keycols = [c for c in self.all_cols if c.name in kcols]
        else:
            self._keycols = [c for c in self.all_cols if c.iskey]
        return self._keycols

    @property
    def valcols(self):
        if self._valcols:
            return self._valcols

        wcols = getattr(self.widget.options, 'columns', None)

        # handle deprecated * option for all columns
        if wcols == '*':
            wcols = None

        if wcols:
            self._valcols = [c for c in self.all_cols
                             if c.name in wcols]
        else:
            # just use all defined columns other than time/key columns
            self._valcols = [c for c in self.all_cols if not c.iskey]

        return self._valcols

    @property
    def colmap(self):
        if self._colmap:
            return self._colmap

        # Map of column info by column name
        colmap = OrderedDict()

        # Build up the colmap
        for i, c in enumerate(self.all_cols):
            if c not in self.keycols and c not in self.valcols:
                continue

            fmt = None
            html = False

            if c.formatter:
                fmt = c.formatter
                html = True
            elif c.isnumeric():
                if c.units == c.UNITS_PCT:
                    fmt = 'formatPct'
                else:
                    if c.datatype == c.DATATYPE_FLOAT:
                        fmt = 'formatMetric'
                    elif c.datatype == c.DATATYPE_INTEGER:
                        fmt = 'formatIntegerMetric'
            elif c.istime():
                fmt = 'formatTime'
            elif c.isdate():
                fmt = 'formatDate'
            elif c.datatype == c.DATATYPE_HTML:
                html = True

            ci = self.ColInfo(c, i, axis=None, fmt=fmt, allow_html=html)
            colmap[c.name] = ci

        self._colmap = colmap
        return self._colmap


class Axes(object):
    def __init__(self, definition):
        self.definition = definition

    def getaxis(self, colname):
        if self.definition is not None:
            for n, v in self.definition.items():
                if ('columns' in v) and (colname in v['columns']):
                    return int(n)
        return 0

    def position(self, axis):
        axis = str(axis)
        if ((self.definition is not None) and
                (axis in self.definition) and
                ('position' in self.definition[axis])):
            return self.definition[axis]['position']
        return 'left'
