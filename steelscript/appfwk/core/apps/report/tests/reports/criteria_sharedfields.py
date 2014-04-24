from steelscript.appfwk.core.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.core.apps.datasource.models import TableField, Column
from steelscript.appfwk.core.libs.fields import Function

from steelscript.appfwk.core.apps.report.models import Report, Section
from steelscript.appfwk.core.apps.report.modules import raw

from steelscript.appfwk.core.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Shared Fields' )
report.save()

x = TableField.create('x', 'X Value')
for i in range(2):

    section = Section(report=report, title='Section %d' % i)
    section.save()

    a = AnalysisTable.create('test-criteria-sharedfields-%d' % i, tables={},
                             function = funcs.analysis_echo_criteria)
    a.add_column('key', 'Key', iskey=True, datatype="string")
    a.add_column('value', 'Value', datatype="string")

    a.fields.add(x)
    y = TableField.create('y', 'Y Value', a,
                          hidden=True,
                          parent_keywords = ['x'],
                          post_process_func = Function(funcs.sharedfields_compute,
                                                       params={'factor': 10*(i+1)}))

    raw.TableWidget.create(section, a, 'Table %d' % i)
