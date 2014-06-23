from django import forms

from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.libs.fields import Function
from steelscript.appfwk.apps.report.models import Report, TableField
from steelscript.appfwk.apps.report.modules import raw
from . import criteria_functions as funcs

report = Report.create(title='Criteria Changing',
                       field_order=['first', 'second'])
section = report.add_section(title='Section 0')

TableField.create('first', 'First Choice', section,
                  field_cls=forms.ChoiceField,
                  field_kwargs={'choices': (('a', 'Option A'),
                                            ('b', 'Option B'))})

TableField.create('second', 'Second Choice', section,
                  field_cls=forms.ChoiceField,
                  pre_process_func=Function(funcs.preprocess_changesecond),
                  dynamic=True)

a = CriteriaTable.create('test-criteria-changingchoices')
report.add_widget(raw.TableWidget, a, 'Table')
