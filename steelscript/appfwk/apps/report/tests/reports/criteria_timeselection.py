from steelscript.appfwk.apps.report.models import Report
import steelscript.appfwk.apps.report.modules.raw as raw
from steelscript.appfwk.apps.datasource.forms import fields_add_time_selection
from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable

report = Report.create(title='Criteria Time Selection')
report.add_section()

a = CriteriaTable.create('test-criteria-timeselection')
fields_add_time_selection(a, initial_duration='1 day')

report.add_widget(raw.TableWidget, a, 'Table')
