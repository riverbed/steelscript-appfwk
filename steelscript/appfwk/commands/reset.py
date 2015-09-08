#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys

from steelscript.commands.steel import BaseCommand, console, shell, prompt_yn


class Command(BaseCommand):
    help = 'Reset App Framework project database'

    def add_options(self, parser):
        parser.add_option('--noinput', action='store_false',
                          dest='interactive', default=True,
                          help='Does NOT prompt for any user input')
        parser.add_option('-v', '--verbose', action='store_true',
                          help='Extra verbose output')

    def main(self):
        cwd = os.getcwd()
        if not os.path.exists('manage.py'):
            console('This command must be run inside the project directory.')
            return

        if self.options.interactive:
            yn = prompt_yn('This will delete and re-initialize the database from '
                           'scratch.  There is no undo.\nAre you sure?', False)
            if not yn:
                console('Aborting.')
                sys.exit()

        shell('python manage.py reset_appfwk --force --trace',
              msg='Resetting project database',
              cwd=cwd)
