# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import inspect

from steelscript.common.exceptions import RvbdHTTPException, RvbdException


def get_request():
    """ Run up the stack and find the `request` object. """
    # XXX see discussion here:
    #    http://nedbatchelder.com/blog/201008/global_django_requests.html
    # alternative would be applying middleware for thread locals
    # if more cases need this behavior, middleware may be better option

    frame = None
    try:
        for f in inspect.stack()[1:]:
            frame = f[0]
            code = frame.f_code
            if code.co_varnames[:1] == ("request",):
                return frame.f_locals["request"]
            elif code.co_varnames[:2] == ("self", "request",):
                return frame.f_locals["request"]
    finally:
        del frame


def get_module(skip_frames=1):
    """ Run up the stack, find the `module` object and return its name.

    This works reasonably well in non-interactive environments when a file
    is being explicitly imported, but will return '__main__' when called
    directly or from an interactive session, like IPython.

    :param int skip_frames: number of stack frames to skip before checking
        for module.  When calling method directly, default of 1 should be
        fine.
    """
    frame, frm, mod = None, None, None

    try:
        for frame in inspect.stack()[skip_frames:]:
            if frame[3] == '<module>':
                frm = frame[0]
                mod = inspect.getmodule(frm)
                # interactive shells will have <module> frame with
                # no corresponding module, skip them
                if hasattr(mod, '__name__'):
                    return mod
        return None
    finally:
        del frame, frm, mod


def get_module_name(module=None):
    """Return module string name.

    :param module: optional module object
    :return: string name or None if invalid module
    """
    if module is None:
        module = get_module(skip_frames=2)

    return getattr(module, '__name__', None)


def get_sourcefile(modname):
    """Return sourcefile name for given module name."""
    if modname is not None:
        return modname
    else:
        return 'default'


def get_namespace(sourcefile):
    """Return namespace for given sourcefile. """
    ns = sourcefile.split('.')

    if (sourcefile.startswith('reports.') and (ns[1] == 'default' or
                                               len(ns) == 2)):
        # 'reports.default', 'reports.overall', etc.
        namespace = 'default'
    elif sourcefile.startswith('custom_reports'):
        namespace = 'custom'
    elif sourcefile.startswith('steelscript.appfwk.apps.plugins.'):
        # 'steelscript.apps.plugins.builtin.whois' --> 'whois'
        namespace = ns[5]
    elif sourcefile.startswith('steelscript.appfwk'):
        # 'steelscript.appfwk.business_hours' --> 'business_hours'
        namespace = ns[2]
    elif sourcefile.startswith('steelscript.'):
        # 'steelscript.wireshark.appfwk.plugin' --> 'wireshark'
        namespace = ns[1]
    elif len(ns) >= 3:
        # take the middle portion, should align to plugin names
        # handles subdirectories as well
        namespace = '.'.join(ns[1:-1])
    else:
        # some other folder structure
        namespace = 'custom'

    return namespace


def get_caller_name(frames_back=2):
    """ Determine filename of calling function.
        Used to determine source of Report class definition.
    """
    frame = inspect.stack()[frames_back]
    frm = frame[0]
    mod = inspect.getmodule(frm)
    del frm
    return mod.__name__


# list of files/directories to ignore
IGNORE_FILES = ['helpers']


class Importer(object):
    """ Helper functions for importing modules. """
    def __init__(self, buf=None):
        if buf is None:
            self.stdout = sys.stdout
        else:
            self.stdout = buf

    def import_file(self, f, name):
        try:
            if name in sys.modules:
                reload(sys.modules[name])
                self.stdout.write('reloading %s as %s\n' % (f, name))
            else:
                __import__(name)
                self.stdout.write('importing %s as %s\n' % (f, name))

        except RvbdHTTPException as e:
            instance = RvbdException('From config file "%s": %s\n' %
                                     (name, e.message))
            raise RvbdException, instance, sys.exc_info()[2]

        except SyntaxError as e:
            msg_format = '%s: (file: %s, line: %s, offset: %s)\n%s\n'
            message = msg_format % (e.msg, e.filename,
                                    e.lineno, e.offset, e.text)
            instance = type(e)('From config file "%s": %s\n' % (name,
                                                                message))
            raise type(e), instance, sys.exc_info()[2]

        except Exception as e:
            instance = type(e)('From config file "%s": %s\n' % (name,
                                                                str(e)))
            raise type(e), instance, sys.exc_info()[2]

    def import_directory(self, root, report_name=None, ignore_list=None):
        """ Recursively imports all python files in a directory
        """
        if ignore_list is None:
            ignore_list = IGNORE_FILES

        rootpath = os.path.basename(root)
        for path, dirs, files in os.walk(root, followlinks=True):
            # if we are in an ignored directory, continue
            if os.path.basename(os.path.normpath(path)) in ignore_list:
                continue

            for f in files:
                if f in ignore_list or not f.endswith('.py') or '__init__' in f:
                    continue

                f = os.path.splitext(f)[0]
                dirpath = os.path.relpath(path, root)
                if dirpath != '.':
                    name = os.path.join(rootpath, dirpath, f)
                else:
                    name = os.path.join(rootpath, f)
                name = '.'.join(name.split(os.path.sep))

                if report_name and report_name != name:
                    self.stdout.write('skipping %s (%s) ...\n' % (f, name))
                    continue

                self.import_file(f, name)
