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
from django.conf import settings

from steelscript.common.timeutils import datetime_to_microseconds

logger = logging.getLogger(__name__)

# Suppress debug logging in elasticsearch.connection.base module
elastic_logger.setLevel(logging.INFO)

MAX_NUMBER_DOCS = 10000

ColumnFilter = namedtuple('ColumnFilter', ['query_type', 'query'])


class ElasticSearch(object):

    def __init__(self):
        logger.debug('Initializing ElasticSearch with hosts: %s' %
                     settings.ELASTICSEARCH_HOSTS)
        self.client = connections.create_connection(
            hosts=settings.ELASTICSEARCH_HOSTS
        )

    def write(self, index, doctype, data_frame, timecol, id_method='time'):
        """ Write `data_frame` to elasticsearch storage.

        :param index: name of index to use
        :param doctype:  elasticsearch `_type` for the records
        :param data_frame: pandas dataframe
        :param timecol: name of the column in data_frame to use for time
        :param id_method: how to generate _id's for each record
            'time' - microseconds of time column
            'unique' - auto-generated unique value by elasticsearch
            tuple - tuple of column names to be combined for each row

        """
        # NOTE:
        # Fix obscure pandas bug with NaT and fillna
        #
        # The error shows "AssertionError: Gaps in blk ref_locs" when
        # executing fillna() on a dataframe that has a pandas.NaT
        # reference in it.
        #
        # Instead of replacing values, just drop them when loading to ES,
        # ES handles the missing items as null
        df = data_frame

        # find whether we have a write alias for the given index
        if index in settings.ES_ROLLOVER:
            index = settings.ES_ROLLOVER[index]['write_index']

        if id_method == 'time':
            _id = lambda x: datetime_to_microseconds(x[timecol])
        elif id_method == 'unique':
            _id = None
        else:
            # we are passed a tuple of columns
            # try to get timestamp value otherwise just use the item itself
            _id = lambda x: ':'.join(str(getattr(x[c], 'value', x[c]))
                                     for c in id_method)

        def gen_actions(data):
            for i, row in data.iterrows():
                action = {
                    '_index': index,
                    '_type': doctype,
                    '_source': row.dropna().to_dict()
                }
                if _id:
                    action['_id'] = _id(row)
                yield action

        logger.debug("Writing %s records from %s to %s into db. Index: %s, "
                     "doc_type: %s."
                     % (len(df), df[timecol].min(), df[timecol].max(),
                        index, doctype))

        logger.debug('Calling Bulk load with client: %s' % self.client)
        written, errors = helpers.bulk(self.client, actions=gen_actions(df),
                                       stats_only=True)
        logger.debug("Successfully wrote %s records, %s errors." % (written,
                                                                    errors))
        return

    def search(self, index, doc_type, col_filters=None):

        # find whether we have a search alias for the given index
        if index in settings.ES_ROLLOVER:
            index = settings.ES_ROLLOVER[index]['search_index']

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
