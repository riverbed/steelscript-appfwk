# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from cStringIO import StringIO
import os
import glob
import optparse
import imp

from django.core.management.base import BaseCommand
from django.core import management
from django.conf import settings
from django import db
from django.db import transaction, DatabaseError

from steelscript.appfwk.apps.preferences.models import SystemSettings, \
    PortalUser

# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Command(BaseCommand):
    args = None
    help = ('Reset the database. Prompts for confirmation unless '
            '`--force` is included as an argument.')

    option_list = BaseCommand.option_list + (
        optparse.make_option('--force',
                             action='store_true',
                             dest='force',
                             default=False,
                             help='Ignore reset confirmation.'),
        optparse.make_option('--drop-users',
                             action='store_true',
                             dest='drop_users',
                             default=False,
                             help='Drop all locally created users, only '
                                  'default admin account will be enabled '
                                  'afterwards. Default will keep all user '
                                  'accounts across reset.'),
    )

    def save_users(self):
        """ Store user definitions to buffer in memory rather than disk. """
        self.stdout.write('Saving existing users ... ', ending='')
        try:
            buf = StringIO()
            management.call_command('dumpscript', 'preferences', stdout=buf)
            buf.seek(0)
            clean_buf = buf.read().replace('<UTC>', 'pytz.UTC')
            clean_buf = clean_buf.replace('import datetime\n',
                                          'import datetime\nimport pytz\n')
            self.user_buffer = clean_buf
        except DatabaseError:
            self.user_buffer = None

        db.close_connection()
        self.stdout.write('done.')

    def load_users(self):
        """ Load stored user module and run it, creating new user objects.

        This script is run under a transaction to avoid committing partial
        settings in case of some exception.
        """
        # ref http://stackoverflow.com/a/14192708/2157429
        if self.user_buffer is not None:
            self.stdout.write('Loading saved users ... ', ending='')
            m = imp.new_module('runscript')
            exec self.user_buffer in m.__dict__
            with transaction.commit_on_success():
                m.run()
            db.close_connection()
            self.stdout.write('done.')

    def handle(self, *args, **options):
        if not options['force']:
            msg = ('You have requested to reset portal, this will delete\n'
                   'everything from the database and start from scratch.\n'
                   'Are you sure?\n'
                   "Type 'yes' to continue, or 'no' to cancel: ")
            confirm = raw_input(msg)
        else:
            confirm = 'yes'

        if confirm != 'yes':
            self.stdout.write('Aborting.')
            return

        self.user_buffer = None
        if not options['drop_users']:
            self.save_users()

        # lets clear it
        self.stdout.write('Resetting database ... ', ending='')
        management.call_command('reset_db',
                                interactive=False,
                                router='default')
        self.stdout.write('done.')

        management.call_command('clean',
                                applications=False,
                                report_id=None,
                                clear_cache=True,
                                clear_logs=True)

        management.call_command('clean_pyc', path=settings.PROJECT_ROOT)

        management.call_command('syncdb', interactive=False)

        self.stdout.write('Loading initial data ... ', ending='')
        initial_data = glob.glob(os.path.join(settings.INITIAL_DATA, '*.json'))
        initial_data.sort()
        if not options['drop_users']:
            # filter out default admin user fixture and reload previous users
            initial_data = [f for f in initial_data if 'admin_user' not in f]

        if initial_data:
            management.call_command('loaddata', *initial_data)

        self.load_users()

        # if we don't have a settings fixture, create new default item
        if not SystemSettings.objects.all():
            SystemSettings().save()

        management.call_command('reload', report_id=None)

        if not options['drop_users'] and (self.user_buffer is None or
                                          len(PortalUser.objects.all()) == 0):
            self.stdout.write('WARNING: No users added to database.  '
                              'If you would like to include the default '
                              'admin user, rerun this command with the '
                              "'--drop-users' option.")
