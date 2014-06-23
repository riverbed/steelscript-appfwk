from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw
from . import criteria_functions as funcs

report = Report.create(title='Criteria Post Process')

section = report.add_section(title='Section 0')

a = CriteriaTable.create('test-criteria-postprocess')

TableField.create('w', 'W Value', a)
TableField.create('x', 'X Value', a)
TableField.create('y', 'Y Value', a)

for (f1, f2) in [('w', 'x'), ('w', 'y'), ('x', 'y')]:
    (TableField.create
     ('%s%s' % (f1, f2), '%s+%s Value' % (f1, f2), a,
      hidden=True, parent_keywords=[f1, f2],
      post_process_func=Function(funcs.postprocess_field_compute,
                                 params={'fields': [f1, f2]})))


report.add_widget(raw.TableWidget, a, 'Table')
