from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

# Report
from steelscript.appfwk.apps.report.tests.reports.synthetic_functions \
    import SyntheticGenerateTable

report = Report.create(title='Widget token test')

# Section
report.add_section(title='Section 0')

# Table
a = SyntheticGenerateTable.create('test-widget-token')

report.add_widget(raw.TableWidget, a, 'Table')
