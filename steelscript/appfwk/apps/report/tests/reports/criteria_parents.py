from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports import criteria_functions as funcs

report = Report.create(title='Criteria Parents',
                       hidden_fields=['report_computed',
                                      'section_computed',
                                      'table_computed'])

# Report-level independent
TableField.create('report_independent', 'Report Independent', obj=report)

# Report-level computed
TableField.create('report_computed', 'Reprot computed', obj=report,
                  post_process_template='report_computed:{report_independent}',
                  hidden=False)

# Section
section = report.add_section(title='Section 0')

# Section-level computed
TableField.create(keyword='section_computed', obj=section,
                  post_process_template='section_computed:{report_computed}',
                  hidden=False)

# Table
a = CriteriaTable.create('test-criteria-parents')

# Table-level computed
TableField.create(keyword='table_computed', obj=a,
                  post_process_template='table_computed:{section_computed}',
                  hidden=False)

report.add_widget(raw.TableWidget, a, 'Table')
