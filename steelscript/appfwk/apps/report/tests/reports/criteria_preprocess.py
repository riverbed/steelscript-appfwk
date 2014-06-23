from django import forms

from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw
from steelscript.appfwk.apps.report.tests.reports \
    import criteria_functions as funcs

report = Report.create(title='Criteria Pre Process')

section = report.add_section(title='Section 0')

TableField.create('choices', 'Choices', section,
                  field_cls=forms.ChoiceField,
                  pre_process_func=Function(funcs.preprocess_field_choices))

TableField.create('choices_with_params', 'Choices with params', section,
                  field_cls=forms.ChoiceField,
                  pre_process_func=
                  Function(funcs.preprocess_field_choices_with_params,
                           params={'start': 1,
                                   'end': 3,
                                   'prefix': 'pre'}))

a = CriteriaTable.create('test-criteria-preprocess')

report.add_widget(raw.TableWidget, a, 'Table')
