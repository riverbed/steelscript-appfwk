from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw

# Reports
from steelscript.appfwk.apps.report.tests.reports.synthetic_functions \
    import SyntheticGenerateTable

report = Report.create(title='Synthetic No Resampling')

# Section
report.add_section(title='Section 0')

# Table
a = SyntheticGenerateTable.create('test-synthetic-noresampling',
                                  source_resolution=60)

report.add_widget(raw.TableWidget, a, 'Table')
