# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import re
import logging
from cStringIO import StringIO
from collections import namedtuple

from django.http import Http404

from django.conf import settings

from rest_framework import views
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.logviewer.forms import LogCriteriaForm


logger = logging.getLogger(__name__)

Log = namedtuple('Log', 'name, full_path, group, disabled')


class LogFinder(object):

    def __init__(self):
        self.logfiles = []
        self.update_logfiles()

    def match_files(self, log_dir, patterns):
        """Return files in `log_dir` that match any of `patterns` regex."""
        regexes = [re.compile(r) for r in patterns]
        try:
            return [os.path.join(log_dir, f)
                    for f in os.listdir(log_dir)
                    for r in regexes
                    if r.match(f)]
        except OSError:
            return []

    def append_logs(self, logs, group):
        self.logfiles.extend(
            Log(os.path.basename(log), log, group, not os.access(log, os.R_OK))
            for log in logs
        )

    def update_logfiles(self):
        """Find valid logfiles on system."""
        logs = self.match_files(settings.LOG_DIR,
                                settings.LOGVIEWER_LOG_PATTERNS)
        self.append_logs(logs, 'Project Logs')

        if settings.LOGVIEWER_ENABLE_SYSLOGS:
            logs = self.match_files(settings.LOGVIEWER_SYSLOGS_DIR,
                                    settings.LOGVIEWER_SYSLOGS_PATTERNS)
            self.append_logs(logs, 'Syslogs')
            logs = self.match_files(settings.LOGVIEWER_CELERY_SYSLOGS_DIR,
                                    settings.LOGVIEWER_CELERY_SYSLOGS_PATTERNS)
            self.append_logs(logs, 'Syslogs')

        if settings.LOGVIEWER_ENABLE_HTTPD_LOGS:
            logs = self.match_files(settings.LOGVIEWER_HTTPD_DIR,
                                    settings.LOGVIEWER_HTTPD_PATTERNS)
            self.append_logs(logs, 'Apache Logs')


def get_log(path, lines, page, filter_expr):
    if filter_expr is not None:
        buf = StringIO()
        regex = re.compile(filter_expr)
        with open(path, 'r') as f:
            for line in f.readlines():
                if regex.search(line):
                    buf.write(line)

        buf.seek(0)
        return tail(buf, lines)

    with open(path, 'r') as f:
        return tail(f, lines)


def tail(f, lines=100):
    """Returns the last `lines` of file `f` as a list.

    :param f: file-like object
    :param lines: number of lines to read from end of file
    """
    # ref http://stackoverflow.com/a/7047765/2157429
    if lines == 0:
        return []

    BUFSIZ = 1024
    f.seek(0, 2)
    block_end_bytes = f.tell()
    size = lines + 1
    block = -1
    data = []

    while size > 0 and block_end_bytes > 0:
        if block_end_bytes - BUFSIZ > 0:
            # Seek back one whole BUFSIZ
            f.seek(block * BUFSIZ, 2)
            # read BUFFER
            data.insert(0, f.read(BUFSIZ))
        else:
            # file too small, start from beginning
            f.seek(0, 0)
            # only read what was not read
            data.insert(0, f.read(block_end_bytes))

        lines_found = data[0].count('\n')
        size -= lines_found
        block_end_bytes -= BUFSIZ
        block -= 1

    text = ''.join(data)
    return text.splitlines()[-lines:]

LOG_TUPLES = LogFinder().logfiles
LOG_MAP = {x.name: x.full_path for x in LOG_TUPLES}


class LogViewer(views.APIView):
    """Process requested log file and display in template."""
    renderer_classes = (TemplateHTMLRenderer,)
    permission_classes = (IsAdminUser,)

    def get(self, request):
        form = LogCriteriaForm(LOG_TUPLES, data=request.GET)

        if form.is_valid():
            data = form.cleaned_data
            if data['logfile'] not in LOG_MAP:
                raise Http404
            path = LOG_MAP[data['logfile']]

            num_lines = data['num_lines']
            page = data['page']  # XXX page is unused for now
            regex = data['regex']

            lines = get_log(path, num_lines, page, regex)

            tagged_lines = []
            for line in lines:
                if '[ERROR]' in line:
                    tag = 'logError'
                elif '[WARNING]' in line:
                    tag = 'logWarning'
                else:
                    tag = 'logNormal'

                tagged_lines.append((tag, line))

            if not tagged_lines:
                # empty logfile
                tagged_lines = [
                    ('logNormal', '\n'),
                    ('logNormal', 'No data found'),
                    ('logNormal', '\n')
                ]

            return Response({'form': form, 'lines': tagged_lines},
                            template_name='logfile.html')
        else:
            if not request.GET:
                # create a blank form
                return Response({'form': LogCriteriaForm(LOG_TUPLES),
                                 'lines': None},
                                template_name='logfile.html')
            else:
                return Response({'form': form, 'lines': None},
                                template_name='logfile.html')
