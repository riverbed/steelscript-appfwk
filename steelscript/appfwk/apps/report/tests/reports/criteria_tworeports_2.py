from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable

from steelscript.appfwk.apps.report.models import Report, Section
from steelscript.appfwk.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Two Reports - 2')
report.save()

TableField.create(keyword='k2', label='Key 2', obj=report, initial='r2')

# Section
section = Section.create(report=report, title='Section')
section.save()

# Table
a = AnalysisTable.create('test-criteria-tworeports-2', tables={},
                         function=funcs.analysis_echo_criteria)
TableField.create(keyword='k1', label='Key 1', obj=a, initial='r1')

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table 2')
