# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

try:
    from logging import NullHandler
except ImportError:
    # Python 2.6 doesn't have NullHandler
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
