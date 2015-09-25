# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import glob
import zipfile
from datetime import datetime

import pytz
from django.conf import settings

from steelscript.commands.steel import shell
from steelscript.common.timeutils import datetime_to_seconds
from steelscript.appfwk.apps.preferences.models import AppfwkUser

import logging
logger = logging.getLogger(__name__)


def debug_fileinfo(fname):
    st = os.stat(fname)
    logging.debug('%15s: mtime - %s, ctime - %s' % (os.path.basename(fname),
                                                    datetime.fromtimestamp(st.st_mtime),
                                                    datetime.fromtimestamp(st.st_ctime)))


def find_logs():
    # returns file paths for all local logs (ignores syslogs)
    files = set()
    for k, v in settings.LOGGING['handlers'].iteritems():
        if 'filename' in v:
            path = v['filename']
            base = os.path.splitext(path)[0] + '*'
            files.update(set(glob.glob(base)))
    return files


def create_debug_zipfile(no_summary=False):
    """ Collects logfiles and system info into a zipfile for download/email

        `no_summary` indicates whether to include system information from
                     the helper script `steel about` as part of the
                     zipped package.  Default is to include the file.
    """
    # setup correct timezone based on admin settings
    admin = AppfwkUser.objects.filter(is_superuser=True)[0]
    tz = pytz.timezone(admin.timezone)
    current_tz = os.environ['TZ']

    try:
        # save TZ to environment for zip to use
        os.environ['TZ'] = str(tz)

        # if zlib is available, then let's compress the files
        # otherwise we will just append them like a tarball
        try:
            import zlib
            compression = zipfile.ZIP_DEFLATED
        except ImportError:
            compression = zipfile.ZIP_STORED

        # setup the name, correct timezone, and open the zipfile
        now = datetime_to_seconds(datetime.now(tz))
        archive_name = os.path.join(settings.PROJECT_ROOT, 'debug-%d.zip' % now)

        myzip = zipfile.ZipFile(archive_name, 'w', compression=compression)

        try:
            # find all of the usual logfiles
            logging.debug('zipping log files ...')
            for fname in find_logs():
                debug_fileinfo(fname)
                myzip.write(fname)

            if not no_summary:
                logging.debug('running about script')
                response = shell('steel about -v', save_output=True)
                logging.debug('zipping about script')
                myzip.writestr('system_summary.txt', response)
        finally:
            myzip.close()

    finally:
        # return env to its prior state
        os.environ['TZ'] = current_tz

    return archive_name
