from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable

from steelscript.appfwk.apps.report.models import Report, TableField
from steelscript.appfwk.apps.report.modules import raw

report = Report.create(title='Criteria Two Reports - 1')

# Section
report.add_section(title='Section')

# Table
a = CriteriaTable.create('test-criteria-tworeports-1')
TableField.create(keyword='k1', label='Key 1', obj=a, initial='r1')

report.add_widget(raw.TableWidget, a, 'Table 1')
