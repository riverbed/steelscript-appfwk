from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

report = Report.create(title='Criteria Defaults')

# Report-level criteria
TableField.create('report-1', 'Report 1', obj=report, initial='r1')
TableField.create('report-2', 'Report 2', obj=report, required=True)

# Section
section = report.add_section(title='Section 0')

# Section-level criteria
TableField.create('section-1', 'Section 1', obj=section, initial='s1')
TableField.create('section-2', 'Section 2', obj=section, required=True, initial='s2')

# Table
a = CriteriaTable.create('test-criteria-defaults')

# Table-level criteria
TableField.create('table-1', 'Table 1', obj=a, initial='t1')
TableField.create('table-2', 'Table 2', obj=a, initial='t2')

report.add_widget(raw.TableWidget, a, 'Table')
