# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django import forms
from django.core.urlresolvers import reverse

import logging
logger = logging.getLogger(__name__)


class LogCriteriaForm(forms.Form):
    logfile = forms.ChoiceField()
    num_lines = forms.IntegerField(initial=100)
    page = forms.IntegerField(initial=1)
    filter_expr = forms.CharField(required=False)

    def __init__(self, valid_logs, *args, **kwargs):
        super(LogCriteriaForm, self).__init__(*args, **kwargs)

        # attributes for template rendering
        self.method = 'GET'
        self.id = 'log-criteria'
        self.action = reverse('logviewer')

        # form fields
        choices = zip(valid_logs, valid_logs)
        self.fields['logfile'] = forms.ChoiceField(choices=choices)

        # page is readonly for now
        self.fields['page'].widget.attrs['readonly'] = 'True'
