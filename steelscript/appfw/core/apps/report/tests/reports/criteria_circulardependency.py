from django import forms

from steelscript.appfw.core.apps.datasource.forms import fields_add_time_selection
from steelscript.appfw.core.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfw.core.apps.datasource.models import TableField, Table, Column
from steelscript.appfw.core.libs.fields import Function

from steelscript.appfw.core.apps.report.models import Report, Section
from steelscript.appfw.core.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Circular Dependency')
report.save()

# Section
section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable.create('test-criteria-circulardependency', tables={},
                         function=funcs.analysis_echo_criteria)

TableField.create(keyword='t1', obj=a,
                  post_process_template='table_computed:{t2}',
                  hidden=False)

TableField.create(keyword='t2', obj=a,
                  post_process_template='table_computed:{t3}',
                  hidden=False)

TableField.create(keyword='t3', obj=a,
                  post_process_template='table_computed:{t1}',
                  hidden=False)

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
