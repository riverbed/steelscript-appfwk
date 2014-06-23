from steelscript.appfwk.apps.datasource.models import TableField

from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

from steelscript.appfwk.apps.report.tests.reports.criteria_functions \
    import CriteriaFieldMapTable

report = Report.create(title='Criteria Defaults')
report.add_section(title='Section 0')

# The table defines two fields 'k1' and 'k2', leave k2 alone, but
# map k1
a = CriteriaFieldMapTable.create('test-criteria-fieldmap-1',
                                 field_map={'k1': 'k1-1'})
report.add_widget(raw.TableWidget, a, 'Table 1')

a = CriteriaFieldMapTable.create('test-criteria-fieldmap-2',
                                 field_map={'k1': {'keyword': 'k1-2',
                                                   'initial': 'K12'}})
report.add_widget(raw.TableWidget, a, 'Table 2')
