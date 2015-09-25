# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from rest_framework.exceptions import APIException


class DatasourceException(APIException):

    status_code = 500

    def __str__(self):
        return "Status %s: %s" % (self.status_code, self.detail)


class TableComputeSyntheticError(DatasourceException):
    """ Exception when something goes wrong with Table.compute_synthetic. """
    status_code = 500
    default_detail = 'Error occurred when calculating synthetic columns.'


class DataError(DatasourceException):
    """ Error processing or retrieving Job data. """
    status_code = 500
    default_detail = 'Error retrieving data for Job.'
