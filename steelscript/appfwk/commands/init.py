#!/usr/bin/env python

import os

from steelscript.commands.steel import BaseCommand, console, shell


class Command(BaseCommand):
    help = 'Initialize App Framework project'

    def main(self):
        cwd = os.getcwd()
        if not os.path.exists('manage.py'):
            console('This command must be run inside the project directory to initialize.')
            return

        shell('python manage.py initialize --trace',
              msg='Initializing project using default settings',
              cwd=cwd)
