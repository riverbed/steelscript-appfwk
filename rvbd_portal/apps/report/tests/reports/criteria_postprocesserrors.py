from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Post Process Errors' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable('test-criteria-postprocess', tables={},
                  function = funcs.analysis_echo_criteria)

TableField.create('error', 'Error type', a.table)
TableField.create('x', 'X Value', a.table, hidden=True,
                  post_process_func = Function(funcs.postprocesserrors_compute))

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a.table, 'Table')
