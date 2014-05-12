from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function

from steelscript.appfwk.apps.report.models import Report, Section
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Post Process' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable.create('test-criteria-postprocess', tables={},
                         function=funcs.analysis_echo_criteria)

TableField.create('w', 'W Value', a)
TableField.create('x', 'X Value', a)
TableField.create('y', 'Y Value', a)

for (f1,f2) in [('w', 'x'), ('w', 'y'), ('x', 'y')]:
    ( TableField.create
      ('%s%s' % (f1, f2), '%s+%s Value' % (f1, f2), a,
       hidden = True, parent_keywords=[f1, f2],
       post_process_func = Function(funcs.postprocess_field_compute,
                                    params={'fields': [f1, f2]})))

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
