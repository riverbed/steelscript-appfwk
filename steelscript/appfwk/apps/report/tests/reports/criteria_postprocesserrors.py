from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports \
    import criteria_functions as funcs

report = Report.create(title='Criteria Post Process Errors')

section = report.add_section(title='Section 0')

a = CriteriaTable.create('test-criteria-postprocess-errors')

TableField.create('error', 'Error type', a)
TableField.create('x', 'X Value', a, hidden=True,
                  post_process_func=Function(funcs.postprocesserrors_compute))


report.add_widget(raw.TableWidget, a, 'Table')
