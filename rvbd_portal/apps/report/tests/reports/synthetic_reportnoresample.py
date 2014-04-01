from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import Column

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw
from rvbd_portal.apps.datasource.forms import fields_add_time_selection, fields_add_resolution

from . import synthentic_functions as funcs

# Report
report = Report(title='Synthetic No Resampling' )
report.save()

# Section
section = Section(report=report, title='Section 0')
section.save()

# Table
a = AnalysisTable('test-synthetic-noresampling', tables={},
                             func = funcs.analysis_echo_criteria)
fields_add_time_selection(table)
fields_add_resolution(table)

a.add_column('time', 'Time', iskey=True, isnumeric=True, datatype='time')
a.add_column('value', 'Value', isnumeric=True)

raw.TableWidget.create(section, a.table, 'Table')
