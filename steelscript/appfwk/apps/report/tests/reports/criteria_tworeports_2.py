from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable

from steelscript.appfwk.apps.report.models import Report, TableField
from steelscript.appfwk.apps.report.modules import raw

report = Report.create(title='Criteria Two Reports - 2')

TableField.create(keyword='k2', label='Key 2', obj=report, initial='r2')

# Section
report.add_section(title='Section')

# Table
a = CriteriaTable.create('test-criteria-tworeports-2')
TableField.create(keyword='k1', label='Key 1', obj=a, initial='r1')

report.add_widget(raw.TableWidget, a, 'Table 2')
