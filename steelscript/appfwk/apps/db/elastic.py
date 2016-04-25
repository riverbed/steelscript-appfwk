# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import time
import logging
import pandas as pd

from collections import namedtuple

from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections
from elasticsearch import helpers

from steelscript.common.timeutils import datetime_to_seconds

logger = logging.getLogger(__name__)

MAX_NUMBER_DOCS = 10000

ColumnFilter = namedtuple('ColumnFilter', ['query_type', 'query'])


class ElasticSearch(object):

    def __init__(self):
        self.client = connections.create_connection(hosts=['localhost'])

    def write(self, index, doctype, data_frame, timecol):

        df = data_frame.fillna('')

        actions = [{"_index": index,
                    "_type": doctype,
                    "_id": datetime_to_seconds(df.iloc[i][timecol]),
                    "_source": df.iloc[i].to_dict()}
                   for i in xrange(len(df))]

        helpers.bulk(self.client, actions=actions)
        logger.debug("Wrote %s records from %s to %s into elasticsearch."
                     % (len(df), df[timecol].min(), df[timecol].max()))
        # Wait a second to give elasticsearch time to commit writting results
        time.sleep(1)
        return

    def search(self, index, doc_type, col_filters=None):
        s = Search(using=self.client, index=index, doc_type=doc_type)
        if col_filters:
            for col_filter in col_filters:
                if isinstance(col_filter, ColumnFilter):
                    s = s.filter(col_filter.query_type, **col_filter.query)
                else:
                    raise ValueError('Column Filter is not an instance of'
                                     ' ColumnFilter class')
        s = s.params(size=MAX_NUMBER_DOCS)

        results = s.execute()

        logger.debug("Search returned %s records from elasticsearch."
                     % len(results))
        return pd.DataFrame([res._d_ for res in results])
