# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import views

from steelscript.appfwk.apps.db import storage, ColumnFilter
from steelscript.common.timeutils import sec_string_to_datetime
from steelscript.appfwk.apps.db.models import ExistingIntervals
from steelscript.appfwk.apps.datasource.modules.ts_table import make_index
from steelscript.appfwk.apps.datasource.models import Table
from steelscript.appfwk.apps.datasource.models import Column
from steelscript.appfwk.apps.db.exceptions import NotFoundError, \
    InvalidRequest

logger = logging.getLogger(__name__)


class Records(views.APIView):

    def get(self, request):
        """ Retrieve records from time series data storage.

        The URL is formatted as '/db/records?handle=**&start=**&end=**'.
        Within the URL, required parameters include 'handle' and 'start'.
        Optional parameter is 'end'. Values for 'start' and 'end' in the
        URL should be epoch seconds. JSON results returned looks like:

        [{"avg_bytes": 1617806.0,
          "time": "2017-03-24T18:14:00+00:00"},
          ...
        ]
        """

        request_data = request.GET.dict()

        keys = ['handle', 'start']
        for k in keys:
            if k not in request_data:
                msg = "Missing parameter '{}' in url".format(k)
                raise InvalidRequest(msg)

        handle = request_data['handle']
        try:
            obj = ExistingIntervals.objects.get(table_handle=handle)
        except ObjectDoesNotExist:
            msg = "Handle '{}' does not exist.".format(handle)
            raise NotFoundError(msg)

        tr = {}
        tr['gte'] = sec_string_to_datetime(int(request_data['start']))
        if 'end' in request_data:
            tr['lte'] = sec_string_to_datetime(int(request_data['end']))

        # Getting the time column name
        table = Table.from_ref(dict(sourcefile=obj.sourcefile,
                                    namespace=obj.namespace,
                                    name=obj.table))

        timecols = [c for c in table.get_columns(iskey=True)
                    if c.datatype == Column.DATATYPE_TIME]

        time_col_name = timecols[0].name

        col_filters = [ColumnFilter(
                       query_type='range',
                       query={time_col_name: tr})]

        records = storage.search(index=make_index(obj.namespace),
                                 doc_type=handle,
                                 col_filters=col_filters)

        return JsonResponse(records, safe=False)


class Handles(views.APIView):

    def get(self, request):
        """ Retrieve time series data handles.

        The URL is formated as '/db/handles/?namespace=**&table=**'.
        Both 'namespace' and 'table' parameters are optional. 'namespace'
        refers to the plugin name while 'table' refers to the name of
        the timeseries source table generating the records.

        JSON results returned look like:
        [{"intervals": "[(2017-03-29 16:16:00+00:00,
                          2017-03-29 17:15:00+00:00),
                        (2017-03-29 18:16:00+00:00,
                         2017-03-29 19:13:00+00:00),
                        ...
                       ]",
          "handle": "d021d2d84a6c0367d9bcfee9f1ac1912",
          "criteria": "{u'netprofiler_filterexpr': u'',
                        'debug': False,
                        u'resolution': datetime.timedelta(0, 60),
                        u'netprofiler_device': u'1',
                        'ignore_cache': False}",
          "table": "ts-overall-db",
          "sourcefile": "reports.netprofiler.netprofiler_db",
          "namespace": "netprofiler"},
          ...
        ]
        """
        request_data = request.GET.dict()

        keys = ['namespace', 'table']
        for k, v in request_data.iteritems():
            if k not in keys:
                msg = "'{}' is not valid to query handles." .format(k)
                raise InvalidRequest(msg)

        res = []
        for obj in ExistingIntervals.objects.filter(**request_data):
            res.append(dict(handle=obj.table_handle,
                            criteria=str(obj.criteria),
                            namespace=obj.namespace,
                            sourcefile=obj.sourcefile,
                            table=obj.table,
                            intervals=str(obj.intervals)))
        return JsonResponse(res, safe=False)
