from django import forms

from steelscript.appfwk.core.apps.datasource.forms import fields_add_time_selection
from steelscript.appfwk.core.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.core.apps.datasource.models import TableField, Table, Column
from steelscript.appfwk.core.libs.fields import Function

from steelscript.appfwk.core.apps.report.models import Report, Section
from steelscript.appfwk.core.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Changing',
                field_order =['first', 'second'])
report.save()

section = Section(report=report, title='Section 0')
section.save()

TableField.create('first', 'First Choice', section,
                  field_cls=forms.ChoiceField,
                  field_kwargs={'choices': (('a', 'Option A'),
                                            ('b', 'Option B'))})

TableField.create('second', 'Second Choice', section,
                  field_cls=forms.ChoiceField,
                  pre_process_func=Function(funcs.preprocess_changesecond),
                  dynamic=True)

a = AnalysisTable.create('test-criteria-changingchoices', tables={},
                         function=funcs.analysis_echo_criteria)
a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
