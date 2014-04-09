from django import forms

from rvbd_portal.apps.datasource.forms import fields_add_time_selection
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Table, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Two Reports - 1')
report.save()

# Section
section = Section.create(report=report, title='Section')
section.save()

# Table
a = AnalysisTable.create('test-criteria-tworeports-1', tables={},
                         function=funcs.analysis_echo_criteria)
TableField.create(keyword='k1', label='Key 1', obj=a, initial='r1')

a.add_column('key', 'Key', iskey=True, datatype="string")
a.add_column('value', 'Value', datatype="string")

raw.TableWidget.create(section, a, 'Table 1')
