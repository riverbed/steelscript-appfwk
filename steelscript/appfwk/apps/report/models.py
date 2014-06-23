# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.conf import settings
from django.db import models
from django.db.models import Max, Sum
from django.template.defaultfilters import slugify
from django.db import transaction
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.utils.datastructures import SortedDict
from django.core.exceptions import ObjectDoesNotExist
from model_utils.managers import InheritanceManager

from steelscript.common.jsondict import JsonDict
from steelscript.appfwk.project.utils import (get_module, get_module_name,
                                              get_sourcefile, get_namespace)
from steelscript.appfwk.apps.datasource.models import Table, Job, TableField
from steelscript.appfwk.libs.fields import \
    PickledObjectField, SeparatedValuesField

logger = logging.getLogger(__name__)


class WidgetOptions(JsonDict):
    _default = {'key': None,
                'value': None,
                'axes': None}


class Report(models.Model):
    """ Defines a Report as a collection of Sections and their Widgets. """
    title = models.CharField(max_length=200)
    position = models.DecimalField(max_digits=7, decimal_places=3, default=10)
    enabled = models.BooleanField(default=True)

    slug = models.SlugField(unique=True)
    namespace = models.CharField(max_length=100)
    sourcefile = models.CharField(max_length=200)
    filepath = models.FilePathField(path=settings.REPORTS_DIR)

    fields = models.ManyToManyField(TableField, null=True, blank=True)
    field_order = SeparatedValuesField(null=True,
                                       default=['starttime', 'endtime',
                                                'duration', 'filterexpr'],
                                       blank=True)
    hidden_fields = SeparatedValuesField(null=True, blank=True)

    # create an 'auto-load'-type report which uses default criteria
    # values only, and optionally set a refresh timer
    hide_criteria = models.BooleanField(default=False)
    reload_minutes = models.IntegerField(default=0)  # 0 means no reloads

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
        :param int reload_minuntes: If non-zero, automatically reloads the report

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

        Sourcefiles will be parsed into the following namespaces:
        'config.reports.1_overall' --> 'default'
        'steelscript.netshark.appfwk.reports.3_shark' --> 'netshark'
        'steelscript.appfwk.business_hours.reports.x_report' --> 'business_hours'
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
        fields_by_section = SortedDict()

        # section id=0 is the "common" section
        # fields attached directly to the Report object are always added
        # to the common section
        fields_by_section[0] = SortedDict()
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

            ordered_field_names = SortedDict()
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
    fields = models.ManyToManyField(TableField, null=True)

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
            posmax = Section.objects.filter(report=report).aggregate(Max('position'))
            position = (posmax['position__max'] or 0) + 1

        section = Section(report=report, title=title, position=position)
        section.save()

        critmode = SectionFieldMode(section=section,
                                    keyword='',
                                    mode=default_field_mode or SectionFieldMode.INHERIT)
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

        fields_by_section = SortedDict()
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

            id = f.keyword
            if id not in fields_by_section[section_id]:
                fields_by_section[section_id][id] = f

        return fields_by_section

    def fields_mode(self, keyword):
        try:
            m = self.sectionfieldmode_set.get(keyword=keyword)
            return m.mode
        except ObjectDoesNotExist: pass

        try:
            m = self.sectionfieldmode_set.get(keyword='')
            return m.mode
        except ObjectDoesNotExist: pass

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
    width = models.IntegerField(default=1)
    height = models.IntegerField(default=300)
    rows = models.IntegerField(default=-1)
    options = PickledObjectField()

    module = models.CharField(max_length=100)
    uiwidget = models.CharField(max_length=100)
    uioptions = PickledObjectField()

    objects = InheritanceManager()

    def __repr__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def __unicode__(self):
        return '<Widget %s (%s)>' % (self.title, self.id)

    def widgettype(self):
        return 'rvbd_%s.%s' % (self.module.split('.')[-1], self.uiwidget)

    def table(self, i=0):
        return self.tables.all()[i]

    def compute_row_col(self):
        rowmax = self.section.report.widgets().aggregate(Max('row'))
        row = rowmax['row__max']
        if row is None:
            row = 1
            col = 1
        else:
            widthsum = self.section.report.widgets().filter(row=row).aggregate(Sum('width'))
            width = widthsum['width__sum']
            if width + self.width > 12:
                row = row + 1
                col = 1
            else:
                col = width + 1
        self.row = row
        self.col = col

    def collect_fields(self):
        # Gather up all fields
        fields = SortedDict()

        # All fields attached to the section's report
        for f in self.section.report.fields.all().order_by('id'):
            fields[f.keyword] = f

        # All fields attached to the section
        for f in self.section.fields.all().order_by('id'):
            fields[f.keyword] = f

        # All fields attached to any Widget's Tables
        for w in self.section.widget_set.all().order_by('id'):
            for t in w.tables.all():
                for f in t.fields.all().order_by('id'):
                    fields[f.keyword] = f

        return fields


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
        with transaction.commit_on_success():
            self.job.reference(str(self))
            super(WidgetJob, self).save(*args, **kwargs)


@receiver(pre_delete, sender=WidgetJob)
def _widgetjob_delete(sender, instance, **kwargs):
    try:
        instance.job.dereference(str(instance))
    except ObjectDoesNotExist:
        logger.info('Job not found for instance %s, ignoring.' % instance)


class Axes:
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
            (axis in self.definition) and ('position' in self.definition[axis])):
            return self.definition[axis]['position']
        return 'left'
