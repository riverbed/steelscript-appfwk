from django import forms

from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Pre Process' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

TableField.create ('choices', 'Choices', section,
                   field_cls = forms.ChoiceField,
                   pre_process_func =
                   Function(funcs.preprocess_field_choices))

TableField.create ('choices_with_params', 'Choices with params', section,
                   field_cls = forms.ChoiceField,
                   pre_process_func =
                   Function(funcs.preprocess_field_choices_with_params,
                            params={'start' : 1,
                                    'end': 3,
                                    'prefix': 'pre'}))

a = AnalysisTable.create('test-criteria-preprocess', tables={},
                         function=funcs.analysis_echo_criteria)
a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
