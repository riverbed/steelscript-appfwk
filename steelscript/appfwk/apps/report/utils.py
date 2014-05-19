# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import glob
import zipfile
import platform
import pkg_resources
from datetime import datetime

import pytz
from django.contrib.auth.models import User

from steelscript.common.timeutils import datetime_to_seconds
from steelscript.commands.steel import shell

from django.conf import settings

import logging
logger = logging.getLogger(__name__)


def debug_fileinfo(fname):
    st = os.stat(fname)
    logging.debug('%15s: mtime - %s, ctime - %s' % (os.path.basename(fname),
                                                    datetime.fromtimestamp(st.st_mtime),
                                                    datetime.fromtimestamp(st.st_ctime)))


def create_debug_zipfile(no_summary=False):
    """ Collects logfiles and system info into a zipfile for download/email

        `no_summary` indicates whether to include system information from
                     the helper script `steel about` as part of the
                     zipped package.  Default is to include the file.
    """
    # setup correct timezone based on admin settings
    admin = User.objects.filter(is_superuser=True)[0]
    tz = pytz.timezone(admin.userprofile.timezone)
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
            filelist = glob.glob(os.path.join(settings.PROJECT_ROOT, 'log*'))

            logging.debug('zipping log files ...')
            for fname in filelist:
                debug_fileinfo(fname)
                myzip.write(fname)

            if not no_summary:
                logging.debug('running about script')
                response = '\n'.join(shell('steel about', save_output=True))
                logging.debug('zipping about script')
                myzip.writestr('system_summary.txt', response)
        finally:
            myzip.close()

    finally:
        # return env to its prior state
        os.environ['TZ'] = current_tz

    return archive_name
