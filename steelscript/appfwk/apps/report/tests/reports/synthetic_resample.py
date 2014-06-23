from steelscript.appfwk.apps.report.models import Report
from steelscript.appfwk.apps.report.modules import raw
from steelscript.appfwk.libs.fields import Function

# Report
from steelscript.appfwk.apps.report.tests.reports.synthetic_functions \
    import SyntheticGenerateTable

report = Report.create(title='Synthetic Resampling')

# Section
report.add_section(title='Section 0')

# Table
a = SyntheticGenerateTable.create('test-synthetic-resampling',
                                  source_resolution=60, resample=True)

report.add_widget(raw.TableWidget, a, 'Table')
