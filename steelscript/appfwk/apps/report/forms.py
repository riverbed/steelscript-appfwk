# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.
import os
import shutil

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django_ace import AceWidget
from django.utils.safestring import mark_safe

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
        fields = '__all__'


class AceReportWidget(AceWidget):
    def render(self, name, value, attrs=None):
        html = super(AceReportWidget, self).render(name, value, attrs)
        # html = '<div class="django-ace-editor">
        # <div style="width: <width>" class="django-ace-toolbar">
        # <a href="./" class="django-ace-max_min"></a></div><html></div>'
        # need to remove the fullscreen button as it causes scrolling to fail
        # after maximizing the editor and then resizing it to normal
        # for now just remove toolbar to avoid this issue

        # add style="display:none" to <a> tag
        class_str = 'class="django-ace-max_min"'
        return mark_safe(html.replace(class_str,
                                      class_str + ' style="display:none"'))


class ReportEditorForm(forms.Form):

    def __init__(self, filepath, *args, **kwargs):
        super(ReportEditorForm, self).__init__(*args, **kwargs)
        self._filepath = filepath
        with open(self._filepath, 'r') as f:
            textdata = f.read()

        widget = AceReportWidget(mode='python', width="100%", height="500px")
        self.fields['text'] = forms.CharField(widget=widget, initial=textdata)

    def is_valid(self):
        return super(ReportEditorForm, self).is_valid()

    def save(self):
        if self.is_valid():
            backup = self._filepath + '.bak'
            try:
                shutil.copyfile(self._filepath, backup)
            except IOError:
                raise ValidationError('unable to create backup file: %s' %
                                      backup)

            try:
                with open(self._filepath, 'w') as f:
                    f.write(self.cleaned_data['text'])
            except IOError:
                raise ValidationError('unable to save file: ' % self._filepath)


class CopyReportForm(forms.Form):
    filename = forms.CharField()
    namespace = forms.CharField()
    reportname = forms.CharField()

    def __init__(self, report, *args, **kwargs):
        super(CopyReportForm, self).__init__(*args, **kwargs)

        # attributes for template rendering
        self.id = 'copyform'
        self.action = reverse('report-editor-copy', args=(report.namespace,
                                                          report.slug))
        self.method = 'POST'

        # form fields
        fname = os.path.basename(report.filepath)
        self.fields['filename'] = forms.CharField(initial=fname)
        self.fields['namespace'] = forms.CharField(initial=report.namespace)
        self.fields['reportname'] = forms.CharField(initial=report.title)

    @property
    def namespace(self):
        return self.cleaned_data.get('namespace')

    @property
    def slug(self):
        return self.cleaned_data.get('filename').split('.')[0]

    @property
    def reportname(self):
        return self.cleaned_data.get('reportname')

    def clean_filename(self):
        filename = self.cleaned_data.get('filename')
        if not filename.endswith('.py'):
            raise ValidationError('filename must end with .py')
        return filename

    def clean(self):
        cleaned_data = super(CopyReportForm, self).clean()
        if not self.errors:
            path = self.filepath(cleaned_data)
            if os.path.exists(path):
                raise ValidationError('File already exists: %s' % path)

            reportname = self.cleaned_data.get('reportname')
            R = Report.objects.all()
            if R.filter(title=reportname):
                raise ValidationError('Report already exists: %s' % reportname)
        return cleaned_data

    def basepath(self):
        """ Base path for report file. """
        return settings.REPORTS_DIR

    def filepath(self, data=None):
        """ Returns filepath using either data or self.cleaned_data.
        """
        if data is None:
            data = self.cleaned_data

        namespace = data.get('namespace', '')
        if namespace == 'default':
            namespace = ''

        return os.path.join(self.basepath(),
                            namespace,
                            data.get('filename'))


class WidgetDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(WidgetDetailForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Widget
        exclude = ['tables', 'module', 'uiwidget', 'uioptions']
