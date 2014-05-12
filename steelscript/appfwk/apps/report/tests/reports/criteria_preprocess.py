from django import forms

from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.report.models import Report, Section
from steelscript.appfwk.apps.report.modules import raw
from steelscript.appfwk.apps.report.tests.reports import criteria_functions as funcs

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
