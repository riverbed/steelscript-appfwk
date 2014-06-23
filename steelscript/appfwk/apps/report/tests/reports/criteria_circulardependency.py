from steelscript.appfwk.apps.datasource.modules.analysis import CriteriaTable

from steelscript.appfwk.apps.report.models import Report, TableField
from steelscript.appfwk.apps.report.modules import raw

report = Report.create(title='Criteria Circular Dependency')
report.add_section()

a = CriteriaTable.create('test-criteria-circulardependency')

TableField.create(keyword='t1', obj=a,
                  post_process_template='table_computed:{t2}',
                  hidden=False)

TableField.create(keyword='t2', obj=a,
                  post_process_template='table_computed:{t3}',
                  hidden=False)

TableField.create(keyword='t3', obj=a,
                  post_process_template='table_computed:{t1}',
                  hidden=False)

report.add_widget(raw.TableWidget, a, 'Table')
