# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import re
import logging
from cStringIO import StringIO

from django.http import Http404

from django.conf import settings

from rest_framework import views
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from steelscript.appfwk.apps.logviewer.forms import LogCriteriaForm


logger = logging.getLogger(__name__)


VALID_LOGS = ['log.txt', 'log.txt.1', 'celery.txt', 'celery.txt.1']
LOG_MAP = {p: os.path.join(settings.DATAHOME, 'logs', p) for p in VALID_LOGS}


def get_log(path, lines, page, filter_expr):
    if filter_expr is not None:
        buf = StringIO()
        ptn = re.compile(filter_expr)
        with open(path, 'r') as f:
            for line in f.readlines():
                if ptn.search(line):
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


class LogViewer(views.APIView):
    """Process requested log file and display in template."""
    renderer_classes = (TemplateHTMLRenderer,)
    permission_classes = (IsAdminUser,)

    def get(self, request):
        form = LogCriteriaForm(VALID_LOGS, data=request.GET)

        if form.is_valid():
            data = form.cleaned_data
            if data['logfile'] not in LOG_MAP:
                raise Http404
            path = LOG_MAP[data['logfile']]

            num_lines = data['num_lines']
            page = data['page']  # XXX page is unused for now
            filter_expr = data['filter_expr']

            lines = get_log(path, num_lines, page, filter_expr)

            tagged_lines = []
            for line in lines:
                if '[ERROR]' in line:
                    tag = 'logError'
                elif '[WARNING]' in line:
                    tag = 'logWarning'
                else:
                    tag = 'logNormal'

                tagged_lines.append((tag, line))

            return Response({'form': form, 'lines': tagged_lines},
                            template_name='logfile.html')
        else:
            if not request.GET:
                # create a blank form
                return Response({'form': LogCriteriaForm(VALID_LOGS),
                                 'lines': None},
                                template_name='logfile.html')
            else:
                return Response({'form': form, 'lines': None},
                                template_name='logfile.html')
