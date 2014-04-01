from django import forms

from rvbd_portal.apps.datasource.forms import fields_add_time_selection
from rvbd_portal.apps.datasource.modules.analysis import AnalysisTable
from rvbd_portal.apps.datasource.models import TableField, Table, Column
from rvbd_portal.libs.fields import Function

from rvbd_portal.apps.report.models import Report, Section
from rvbd_portal.apps.report.modules import raw

from . import criteria_functions as funcs

report = Report(title='Criteria Section Keywords')
report.save()


# Section
section = Section.create(report=report, title='Section 0', section_keywords=['k1'])
section.save()

# Table
a = AnalysisTable('test-criteria-sectionkeywords-1', tables={},
                  function = funcs.analysis_echo_criteria)
TableField.create(keyword='k1', label='Key 1', obj=a.table, initial='r1')

a.add_column('key', 'Key', iskey=True, isnumeric=False)
a.add_column('value', 'Value', isnumeric=False)

raw.TableWidget.create(section, a.table, 'Table 1')

# Section
section = Section.create(report=report, title='Section 1', section_keywords=['k1'])
section.save()

# Table
a = AnalysisTable('test-criteria-sectionkeywords-2', tables={},
                  function = funcs.analysis_echo_criteria)
TableField.create(keyword='k1', label='Key 1', obj=a.table, initial='r1')

a.add_column('key', 'Key', iskey=True, isnumeric=False)
a.add_column('value', 'Value', isnumeric=False)

raw.TableWidget.create(section, a.table, 'Table 2')
