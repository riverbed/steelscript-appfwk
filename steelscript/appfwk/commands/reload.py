#!/usr/bin/env python

import os

from steelscript.commands.steel import BaseCommand, console, shell


class Command(BaseCommand):
    help = 'Reload installed reports within an App Framework project'

    def main(self):
        cwd = os.getcwd()
        if not os.path.exists('manage.py'):
            console('This command must be run inside the project directory.')
            return

        shell('python manage.py reload --trace',
              msg='Reloading app framework reports',
              cwd=cwd)
