# Copyright (c) 2015 Riverbed Technology, Inc.
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
    AppfwkUser
from steelscript.common import RvbdException

# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Command(BaseCommand):
    args = ''
    help = ('Reset the database. Prompts for confirmation unless '
            '`--force` is included as an argument.')

    # users need to be loaded first as foreign keys in tokens
    # keys need to the latter half of the drop options
    # for key 'users', 'drop_' + 'users' equals to option 'drop_users'

    # originally used OrderedDict, unfortunately it is not supported in
    # Python2.6. In order to maintain the plug-and-play feature of drop
    # options (Just change the static attributes to add one drop option),
    # introduced buffer_names list to keep order of loading sequeces of
    # different buffers
    buffer_names = ['users', 'tokens']
    buffers = {'users': {'model': 'preferences.AppfwkUser',
                         'buffer': None},
               'tokens': {'model': 'report.WidgetAuthToken',
                          'buffer': None},
               }

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
        optparse.make_option('--drop-tokens',
                             action='store_true',
                             dest='drop_tokens',
                             default=False,
                             help='Drop all widget authentication tokens. '
                                  'After the operation, all existing embedded '
                                  'widgets will fail on authentication')
    )

    def save_data(self, name):
        """ Store model definitions to buffer in memory rather than disk. """
        self.stdout.write('Saving existing %s ... ' % name, ending='')
        try:
            buf = StringIO()
            management.call_command('dumpscript', self.buffers[name]['model'],
                                    stdout=buf)
            buf.seek(0)
            clean_buf = buf.read().replace('<UTC>', 'pytz.UTC')
            clean_buf = clean_buf.replace('import datetime\n',
                                          'import datetime\nimport pytz\n')
        except DatabaseError:
            clean_buf = None

        self.buffers[name]['buffer'] = clean_buf

        db.connections.close_all()
        self.stdout.write('done.')

    def load_data(self, name):
        """ Load stored model module and run it, creating new model objects.

        This script is run under a transaction to avoid committing partial
        settings in case of some exception.
        """
        # ref http://stackoverflow.com/a/14192708/2157429
        buf = self.buffers[name]['buffer']
        if buf is not None:
            self.stdout.write('Loading saved %s ...' % name, ending='')
            m = imp.new_module('runscript')
            exec buf in m.__dict__
            with transaction.atomic():
                m.run()
            db.connections.close_all()
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

        # Iterating keys in buffers and save data based on options
        for name in self.buffer_names:
            if not options['drop_' + name]:
                self.save_data(name)

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

        # some chain of migration dependencies requires this first
        # https://code.djangoproject.com/ticket/24524
        management.call_command('migrate', 'preferences', interactive=False)

        # now we can do the full migrate (previously syncdb)
        management.call_command('migrate', interactive=False)

        self.stdout.write('Loading initial data ... ', ending='')
        initial_data = glob.glob(os.path.join(settings.INITIAL_DATA, '*.json'))
        initial_data.sort()
        if not options['drop_users']:
            # filter out default admin user fixture and reload previous users
            initial_data = [f for f in initial_data if 'admin_user' not in f]

        if initial_data:
            management.call_command('loaddata', *initial_data)

        for name in self.buffer_names:
            self.load_data(name)

        # if we don't have a settings fixture, create new default item
        if not SystemSettings.objects.all():
            SystemSettings().save()

        management.call_command('reload', report_id=None)

        if (not options['drop_users'] and
            (self.buffers['users']['buffer'] is None or
             len(AppfwkUser.objects.all()) == 0)):
            self.stdout.write('WARNING: No users added to database.  '
                              'If you would like to include the default '
                              'admin user, rerun this command with the '
                              "'--drop-users' option.")

        # reset progressd cache
        self.stdout.write('Resetting progressd ...', ending='')
        try:
            from steelscript.appfwk.apps.jobs.progress import progressd
            progressd.reset()
        except RvbdException:
            self.stdout.write(' unable to connect to progressd, skipping ...',
                              ending='')
        self.stdout.write(' done.')
