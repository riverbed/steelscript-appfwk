from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField
from steelscript.appfwk.libs.fields import Function

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports \
    import criteria_functions as funcs

report = Report.create(title='Criteria Shared Fields')

x = TableField.create('x', 'X Value')
for i in range(2):

    section = report.add_section(title='Section %d' % i)

    a = CriteriaTable.create('test-criteria-sharedfields-%d' % i)

    a.fields.add(x)
    y = TableField.create(
        'y', 'Y Value', a, hidden=True,
        parent_keywords=['x'],
        post_process_func=Function(funcs.sharedfields_compute,
                                   params={'factor': 10*(i+1)}))

    report.add_widget(raw.TableWidget, a, 'Table %d' % i)
