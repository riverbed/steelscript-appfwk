from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Post Process' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable('test-criteria-postprocess', tables={},
                  function = funcs.analysis_echo_criteria)

TableField.create('w', 'W Value', a.table)
TableField.create('x', 'X Value', a.table)
TableField.create('y', 'Y Value', a.table)

for (f1,f2) in [('w', 'x'), ('w', 'y'), ('x', 'y')]:
    ( TableField.create
      ('%s%s' % (f1, f2), '%s+%s Value' % (f1, f2), a.table,
       hidden = True, parent_keywords=[f1, f2],
       post_process_func = Function(funcs.postprocess_field_compute,
                                    params={'fields': [f1, f2]})))

a.add_column('key', 'Key', iskey=True, isnumeric=False)
a.add_column('value', 'Value', isnumeric=False)

raw.TableWidget.create(section, a.table, 'Table')
