from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Column

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from rvbd_portal.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Defaults')
report.save()

# Report-level criteria
TableField.create(keyword='report-1', label='Report 1', obj=report, initial='r1')
TableField.create(keyword='report-2', label='Report 2', obj=report, required=True)

# Section
section = Section(report=report, title='Section 0')
section.save()

# Section-level criteria
TableField.create(keyword='section-1', label='Section 1', obj=section, initial='s1')
TableField.create(keyword='section-2', label='Section 2', obj=section, required=True, initial='s2')

# Table
a = AnalysisTable('test-criteria-postprocess', tables={},
                  function = funcs.analysis_echo_criteria)

# Table-level criteria
TableField.create(keyword='table-1', label='Table 1', obj=a.table, initial='t1')
TableField.create(keyword='table-2', label='Table 2', obj=a.table, initial='t2')


a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a.table, 'Table')
