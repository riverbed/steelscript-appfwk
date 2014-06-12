# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django import forms
from django_ace import AceWidget

from steelscript.appfwk.apps.report.models import Report, Widget

import logging
logger = logging.getLogger(__name__)

DURATIONS = ('Default', '15 min', '1 hour', 
             '2 hours', '4 hours', '12 hours', '1 day',
             '1 week', '4 weeks')


class ReportDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ReportDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Report


class AceReportWidget(AceWidget):
    def render(self, name, value, attrs=None):
        return super(AceReportWidget, self).render(name, value, attrs)


class ReportEditorForm(forms.Form):

    def __init__(self, filepath, *args, **kwargs):
        super(ReportEditorForm, self).__init__(*args, **kwargs)
        self._filepath = filepath
        with open(self._filepath, 'r') as f:
            widget = AceReportWidget(mode='python', width="100%", height="500px")
            self.fields['text'] = forms.CharField(widget=widget,
                                                  initial=f.read())

    def is_valid(self):
        return super(ReportEditorForm, self).is_valid()

    def save(self):
        if self.is_valid():
            with open(self._filepath, 'w') as f:
                f.write(self.cleaned_data['text'])


class WidgetDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(WidgetDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Widget
        exclude = ['tables', 'module', 'uiwidget', 'uioptions']
