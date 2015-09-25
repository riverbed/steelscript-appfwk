# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from itertools import groupby

from django import forms
from django.forms.widgets import Select
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape
from django.core.urlresolvers import reverse

import logging
logger = logging.getLogger(__name__)


class SelectWithDisabled(Select):
    """
    Subclass of Django's select widget that allows disabling options.
    To disable an option, pass a dict instead of a string for its label,
    of the form: {'label': 'option label', 'disabled': True}
    """
    # https://djangosnippets.org/snippets/2453/

    def render_option(self, selected_choices, option_value, option_label):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
        else:
            selected_html = ''
        disabled_html = ''
        if isinstance(option_label, dict):
            if dict.get(option_label, 'disabled'):
                disabled_html = u' disabled="disabled"'
            option_label = option_label['label']
        return u'<option value="%s"%s%s>%s</option>' % (
            escape(option_value), selected_html, disabled_html,
            conditional_escape(force_unicode(option_label))
        )


class LogCriteriaForm(forms.Form):
    logfile = forms.ChoiceField()
    num_lines = forms.IntegerField(initial=100)
    page = forms.IntegerField(initial=1)
    regex = forms.CharField(label='RegEx', required=False)

    def __init__(self, log_tuples, *args, **kwargs):
        super(LogCriteriaForm, self).__init__(*args, **kwargs)

        # attributes for template rendering
        self.method = 'GET'
        self.id = 'log-criteria'
        self.action = reverse('logviewer')

        # Create a grouped tuple for the select box
        choices = tuple(
            (k, sorted(
                (log.name,
                 {'label': log.name, 'disabled': log.disabled}) for log in g
            ))
            for k, g in groupby(log_tuples, lambda x: x.group)
        )
        self.fields['logfile'] = forms.ChoiceField(choices=choices,
                                                   widget=SelectWithDisabled())

        # page is readonly for now
        self.fields['page'].widget.attrs['readonly'] = 'True'
