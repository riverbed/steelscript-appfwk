# Copyright (c) 2017 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

from rest_framework.exceptions import APIException


class NotFoundError(APIException):
    """ No object found for the handle. """
    status_code = 404
    default_detail = 'Data not found.'


class InvalidRequest(APIException):
    """Invalid query parameter error. """
    status_code = 400
    default_detail = "Invalid request."
