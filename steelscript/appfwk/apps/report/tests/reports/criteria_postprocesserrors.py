from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function

from steelscript.appfwk.apps.report.models import Report, Section
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Post Process Errors' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable.create('test-criteria-postprocess', tables={},
                         function=funcs.analysis_echo_criteria)

TableField.create('error', 'Error type', a)
TableField.create('x', 'X Value', a, hidden=True,
                  post_process_func = Function(funcs.postprocesserrors_compute))

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
