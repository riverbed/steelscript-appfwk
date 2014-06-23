import logging

from steelscript.appfwk.apps.datasource.modules.analysis \
    import CriteriaTable, CriteriaQuery
from steelscript.appfwk.apps.datasource.models import TableField


logger = logging.getLogger(__name__)


def preprocess_field_choices(form, id, field_kwargs, params):
    field_kwargs['choices'] = [('val1', 'Value 1'),
                               ('val2', 'Value 2'),
                               ('val3', 'Value 3')]


def preprocess_field_choices_with_params(form, id, field_kwargs, params):
    choices = []
    for i in range(params['start'], params['end']+1):
        val = params['prefix'] + '_val' + str(i)
        choices.append((val, val))

    field_kwargs['choices'] = choices


def preprocess_changesecond(form, id, field_kwargs, params):
    first_val = form.get_field_value('first', id)
    field_kwargs['choices'] = [(first_val + ('-%d' % i),
                                'Choice %d' % i)
                               for i in range(3)]


def postprocess_field_compute(form, id, criteria, params):
    s = 0
    for f in params['fields']:
        s = s + int(criteria[f])

    criteria[id] = s


def sharedfields_compute(form, id, criteria, params):
    criteria[id] = str(int(criteria['x']) * 2 + int(params['factor']))


def postprocesserrors_compute(form, id, criteria, params):
    if criteria['error'] == 'syntax':
        # Intentional syntax error
        adsf
    else:
        criteria['x'] = 1


class CriteriaFieldMapTable(CriteriaTable):
    class Meta:
        proxy = True

    _query_class = 'CriteriaQuery'

    def post_process_table(self, field_options):
        super(CriteriaFieldMapTable, self).post_process_table(field_options)
        TableField.create('k1', 'Key 1', obj=self, initial='K1')
        TableField.create('k2', 'Key 2', obj=self, required=True)
