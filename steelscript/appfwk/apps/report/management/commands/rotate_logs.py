# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import logging

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    args = ''
    help = 'Rotates log files.'

    def handle(self, *args, **options):
        db_logger = logging.getLogger('django.db.backends')
        db_logger.info('*** rolling db log ***')
        for h in db_logger.handlers:
            try:
                h.doRollover()
            except AttributeError:
                pass

        # there seems to be a hierarchy so we need to call
        # the module parent logger to get to the actual logHandler
        logger = logging.getLogger(__name__)
        logger.info('*** rolling default log ***')
        for h in logger.parent.handlers:
            try:
                h.doRollover()
            except AttributeError:
                pass
