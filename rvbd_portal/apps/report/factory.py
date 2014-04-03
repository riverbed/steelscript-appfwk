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
from rvbd_portal.apps.report.models import (Report, Section, SectionFieldMode,
                                            WidgetOptions)


logger = logging.getLogger(__name__)


class ReportFactory(object):
    """ Factory class for Reports and its components. """
    REPORT_OPTIONS = {
        # model options
        'position': 0,
        'field_order': None,
        'hidden_fields': None,
        'hide_criteria': False,
        'reload_minutes': 0,
    }

    SECTION_OPTIONS = {
        # model options
        'position': 0,
        # field options
        'section_keywords': None,
        'default_field_mode': None,
        'keyword_field_modes': None,
    }

    def __init__(self, report_title, **kwargs):
        """ Initialize object. """
        self.report_title = report_title
        self.report = None
        self.sections = []
        self.widgets = []

        # make class vars local to instance
        report_options = copy.deepcopy(self.REPORT_OPTIONS)
        self.report_options = self.validate_args(report_options, **kwargs)

        # handle custom defaults
        self.pre_process_report()
        self.create_report()
        # add custom fields, etc
        self.post_process_report()

    def validate_args(self, options, **kwargs):
        """ Process keyword arguments and raise error if invalid items found.
        """
        keys = kwargs.keys()
        values = dict((k, kwargs.pop(k)) for k in keys if k in options)
        options.update(**values)

        if kwargs:
            raise AttributeError('Invalid keyword arguments: %s' % str(kwargs))

        return options

    def pre_process_report(self):
        """ Process arguments / defaults before table creation.
        """
        pass

    def create_report(self):
        """ Create a report. """

        logger.debug('Creating report %s' % self.report_title)
        self.report = Report(title=self.report_title, **self.report_options)
        self.report.save()

    def post_process_report(self):
        """ Hook to add custom fields, or other post-report creation operations.
        """
        pass

    def add_section(self, title, **kwargs):
        """ Create a column object. """
        options = copy.deepcopy(self.SECTION_OPTIONS)
        section_options = self.validate_args(options, **kwargs)

        s = Section.create(self.report, title, **section_options)
        self.sections.append(s)

        return s

    def add_widget(self, cls, table, title, **kwargs):
        if len(self.sections) == 0:
            raise ValueError('Widgets can only be added to Sections. '
                             'Add section using "add_section" method first.')

        s = kwargs.pop('section', self.sections[-1])
        t = getattr(table, 'table', table)

        return cls.create(s, t, title, **kwargs)
