# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import re
import os
import sys

from steelscript.commands.steel import (BaseCommand, shell, prompt, prompt_yn,
                                        check_git, ShellFailed)
import steelscript.appfwk.commands


def process_file(src, dst, options):
    srcf = open(src, 'r')
    dstf = open(dst, 'w')

    for i, line in enumerate(srcf):
        line = line.rstrip()
        while True:
            m = re.match("^(.*){{([^}]+)}}(.*)$", line)
            if m is None:
                break

            k = m.group(2)
            try:
                val_escaped = (options[k].encode('unicode-escape')
                               ).replace("'", "\\'")
                line = (m.group(1) + val_escaped + m.group(3))
            except:
                print ("Failed to process {file}:{i} - key {key}:\n{line}"
                       .format(file=src, i=i, key=k, line=line))
                sys.exit(1)

        dstf.write(line + '\n')

    srcf.close()
    dstf.close()


class Command(BaseCommand):
    help = 'Create a new SteelScript Application Framework plugin'

    def add_options(self, parser):
        parser.add_option('-n', '--name',
                          help='Simple name for the plugin')

        parser.add_option('-t', '--title', default='',
                          help='Title for the plugin')

        parser.add_option('-D', '--description', default='',
                          help='Short description')

        parser.add_option('-a', '--author', default='',
                          help="Author's name")

        parser.add_option('-e', '--author-email', default='',
                          help="Author's email")

        parser.add_option('--non-interactive', action='store_true',
                          help='Accept defaults for all options not specified')

        parser.add_option('-d', '--dir', default='.',
                          help='Location to create the new package')

        parser.add_option('-w', '--wave', action='store_true',
                          help='Create the sample wave plugin rather than '
                               'empty')

        parser.add_option('--nogit', action='store_true',
                          help='Do not initialize project as new git repo')

    def initialize_git(self, dirpath):
        """If git installed, initialize project folder as new repo.
        """
        try:
            check_git()
        except ShellFailed:
            return False

        # we have git, lets make a repo
        shell('git init', msg='Initializing project as git repo',
              cwd=dirpath)
        shell('git add .',
              msg=None,
              cwd=dirpath)
        shell('git commit -a -m "Initial commit."',
              msg='Creating initial git commit',
              cwd=dirpath)
        shell('git tag -a 0.0.1 -m 0.0.1',
              msg='Tagging as release 0.0.1',
              cwd=dirpath)
        return True

    def main(self):
        options = self.options
        interactive = not options.non_interactive

        if options.wave:
            if options.name and options.name != 'wave':
                self.parser.error("Name may not be specified for the sample "
                                  "WaveGenerator plugin")
                sys.exit(1)

            options.name = 'wave'
            options.title = 'Sample WaveGenerator'
            options.description = 'Generate sine and cosine waves'
            options.author = 'Riverbed'
            options.author_email = 'eng-github@riverbed.com'
        else:
            # Ask questions
            if options.name:
                if not re.match('^[a-z0-9_]+$', options.name):
                    self.parser.error('Invalid name: please use only '
                                      'lowercase letters, numbers, and '
                                      'underscores.\n')
            else:
                done = False
                while not done:
                    options.name = prompt(
                        'Give a simple name for your plugin (a-z, 0-9, _)')

                    if not re.match('^[a-z0-9_]+$', options.name):
                        self.parser.error('Invalid name: please use only '
                                          'lowercase letters, numbers, and '
                                          'underscores.\n')
                    else:
                        done = True

            if not options.title and interactive:
                options.title = prompt('Give your plugin a title', default='')

            if not options.description and interactive:
                options.description = prompt('Briefly describe your plugin',
                                             default='')

            if not options.author and interactive:
                options.author = prompt("Author's name", default='')

            if not options.author_email and interactive:
                options.author_email = prompt("Author's email", default='')

        options.Name = options.name[0:1].upper() + options.name[1:]
        if not options.title:
            options.title = options.name

        which = 'wave' if options.wave else '__plugin__'

        basedir = os.path.join(
            os.path.dirname(steelscript.appfwk.commands.__file__),
            'data', 'steelscript-' + which)
        targetbasedir = os.path.join(os.path.abspath(options.dir),
                                     'steelscript-' + options.name)
        for (dir, subdirs, files) in os.walk(basedir):
            targetdir = dir.replace(basedir, targetbasedir)
            targetdir = targetdir.replace(which, options.name)
            if dir == basedir:
                if os.path.exists(targetdir):
                    self.parser.error(('Target directory already exists: '
                                       '{0}').format(targetdir))

            os.mkdir(targetdir.format(which=options.name))

            for f in files:
                if (  f.endswith('~') or
                      f.endswith('.pyc') or
                      f.endswith('#')):
                    continue

                srcfile = os.path.join(dir, f)
                dstfile = os.path.join(targetdir,
                                       (f.replace('.py.in', '.py')
                                         .replace(which, options.name)))

                process_file(srcfile, dstfile, vars(options))
                print('Writing:  {dst}'.format(dst=dstfile))

        shell('(cd {dir}; python setup.py develop )'.format(dir=targetbasedir))

        write_relver = True

        if not self.options.nogit:
            if self.initialize_git(targetbasedir):
                write_relver = False

        if write_relver:
            relver = open(os.path.join(targetbasedir, 'RELEASE-VERSION'), 'w')
            relver.write('0.0.1')
            relver.close()
