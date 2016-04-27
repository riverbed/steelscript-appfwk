# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from django.http import JsonResponse

from rest_framework import views
from rest_framework.renderers import JSONRenderer

from steelscript.appfwk.apps.db import storage, ColumnFilter
from steelscript.common.timeutils import sec_string_to_datetime

logger = logging.getLogger(__name__)


class DBQuery(views.APIView):
    """View class of querying db"""

    rederer_classes = (JSONRenderer, )

    def get(self, request):

        # request is constructed as:
        # db/query?plugin=**&handle=**&start=**&end=**&timecol=
        request_data = request.GET.dict()

        keys = ['plugin', 'handle', 'start', 'end', 'timecol']
        for k in keys:
            if k not in request_data:
                raise KeyError("Missing '%s' parameter in url" % k)

        plugin = request_data['plugin']
        handle = request_data['handle']
        start_time = sec_string_to_datetime(int(request_data['start']))
        end_time = sec_string_to_datetime(int(request_data['end']))

        time_col = request_data['timecol']
        col_filters = [ColumnFilter(
                       query_type='range',
                       query={time_col: {'gte': start_time,
                                         'lte': end_time}})]

        df = storage.search(index=plugin,
                            doc_type=handle,
                            col_filters=col_filters)

        return JsonResponse(df.to_dict('records'), safe=False)
