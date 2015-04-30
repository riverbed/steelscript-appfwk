# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from rest_framework.exceptions import APIException


class SteelScriptDatasourceException(Exception):
    pass


class TableComputeSyntheticError(APIException):
    """ Exception when something goes wrong with Table.compute_synthetic. """
    status_code = 500
    default_detail = 'Error occurred when calculating synthetic columns.'


class DataError(APIException):
    """ Error processing or retrieving Job data. """
    status_code = 500
    default_detail = 'Error retrieving data for Job.'
