# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from django.conf import settings
from models import ExistingIntervals

if (not hasattr(settings, 'DB_SOLUTION')):
    raise Exception('settings.DB_SOLUTION not set')

elif (settings.DB_SOLUTION == 'elastic') or settings.TESTING:
    from steelscript.appfwk.apps.db.elastic import ElasticSearch, ColumnFilter
    storage = ElasticSearch()

else:
    raise Exception('Unrecognized settings.DB_SOLUTION: %s' %
                    settings.DB_SOLUTION)
