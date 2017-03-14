# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import logging

from collections import namedtuple

from elasticsearch_dsl import Search
from elasticsearch_dsl.connections import connections
from elasticsearch import helpers
from elasticsearch.connection.base import logger as elastic_logger

from steelscript.common.timeutils import datetime_to_seconds
from steelscript.appfwk.project.settings import ELASTICSEARCH_HOSTS

logger = logging.getLogger(__name__)

# Suppress debug logging in elasticsearch.connection.base module
elastic_logger.setLevel(logging.INFO)

MAX_NUMBER_DOCS = 10000

ColumnFilter = namedtuple('ColumnFilter', ['query_type', 'query'])


class ElasticSearch(object):

    def __init__(self):
        self.client = connections.create_connection(hosts=ELASTICSEARCH_HOSTS)

    def write(self, index, doctype, data_frame, timecol):

        df = data_frame.fillna('')

        actions = [{"_index": index,
                    "_type": doctype,
                    "_id": datetime_to_seconds(df.iloc[i][timecol]),
                    "_source": df.iloc[i].to_dict()}
                   for i in xrange(len(df))]

        logger.debug("Writing %s records from %s to %s into db. Index: %s, "
                     "doc_type: %s."
                     % (len(df), df[timecol].min(), df[timecol].max(),
                        index, doctype))

        written, errors = helpers.bulk(self.client, actions=actions,
                                       stats_only=True)
        logger.debug("Successfully wrote %s records, %s errors." % (written,
                                                                    errors))
        return

    def search(self, index, doc_type, col_filters=None):

        logger.debug("Searching index %s for doc_type %s and col_filters %s"
                     % (index, doc_type, col_filters))

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
        return [res.to_dict() for res in results]
