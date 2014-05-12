from steelscript.appfwk.apps.report.models import Report, Section
import steelscript.appfwk.apps.report.modules.raw as raw
from steelscript.appfwk.apps.datasource.forms import fields_add_time_selection
from steelscript.appfwk.apps.datasource.modules.analysis import AnalysisTable
from steelscript.appfwk.apps.report.tests.reports import criteria_functions as funcs

report = Report(title='Criteria Time Selection' )
report.save()

section = Section(report=report, title='Section 0')
section.save()

a = AnalysisTable.create('test-criteria-timeselection', tables={},
                         function=funcs.analysis_echo_criteria)
fields_add_time_selection(a, initial_duration='1 day')

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table')
