from django import forms

from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable
from steelscript.appfwk.apps.datasource.models import TableField

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

report = Report.create(title='Criteria Bool')

# Section
section = report.add_section(title='Section 0')

# Table
a = CriteriaTable.create('test-criteria-bool')

# Table-level criteria
TableField.create('b1', 'Bool True', obj=a,
                  field_cls=forms.BooleanField, initial=True)
TableField.create('b2', 'Bool False', obj=a,
                  field_cls=forms.BooleanField, initial=False)

report.add_widget(raw.TableWidget, a, 'Table')
