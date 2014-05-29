# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import glob
import shutil
import inspect
import pkg_resources

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


def get_module():
    """ Run up the stack, find the `module` object and return its name.

    This works reasonably well in non-interactive environments when a file
    is being explicitly imported, but will return '__main__' when called
    directly or from an interactive session, like IPython.
    """
    frame, frm, mod = None, None, None

    try:
        for frame in inspect.stack()[1:]:
            if frame[3] == '<module>':
                frm = frame[0]
                mod = inspect.getmodule(frm)
                # interactive shells will have <module> frame with
                # no corresponding module, skip them
                if hasattr(mod, '__name__'):
                    return mod.__name__
        return None
    finally:
        del frame, frm, mod


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
    elif ns[0] == 'steelscript':
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


def link_pkg_dir(pkgname, src_path, dest_dir, symlink=True,
                 replace=True, buf=None):
    """Create a link from a resource within an installed package.

    :param pkgname: name of installed package
    :param src_path: relative path within package to resource
    :param dest_dir: absolute path to location to link/copy
    :param symlink: create a symlink or copy files
    :param replace: if True, will unlink/delete before linking
    :param buf: IO buffer to send debug statements, if None uses sys.stdout
    """
    if buf is None:
        debug = sys.stdout.write
    else:
        debug = buf

    src_dir = pkg_resources.resource_filename(pkgname, src_path)

    if os.path.islink(dest_dir) and not os.path.exists(dest_dir):
        debug(' unlinking %s ...\n' % dest_dir)
        os.unlink(dest_dir)

    if os.path.exists(dest_dir):
        if not replace:
            return

        if os.path.islink(dest_dir):
            debug(' unlinking %s ...\n' % dest_dir)
            os.unlink(dest_dir)
        else:
            debug(' removing %s ...\n' % dest_dir)
            shutil.rmtree(dest_dir)

    if symlink:
        debug(' linking %s --> %s\n' % (src_dir, dest_dir))
        os.symlink(src_dir, dest_dir)
    else:
        debug(' copying %s --> %s\n' % (src_dir, dest_dir))
        shutil.copytree(src_dir, dest_dir)


def link_pkg_files(pkgname, src_pattern, dest_dir, symlink=True,
                   replace=True, buf=None):
    """Create links for files from a resource within an installed package.

    :param pkgname: name of installed package
    :param src_pattern: relative path within package to file resource,
        can be a glob pattern
    :param dest_dir: absolute path to location to link/copy, symlinks
        will be made inside this dir rather than linking to the dir itself
    :param symlink: create a symlink or copy files
    :param replace: if True, will unlink/delete before linking
    :param buf: IO buffer to send debug statements, if None uses sys.stdout
    """
    if buf is None:
        debug = sys.stdout.write
    else:
        debug = buf

    src_dir = pkg_resources.resource_filename(pkgname, src_pattern)
    src_files = glob.glob(src_dir)

    if os.path.islink(dest_dir):
        # avoid putting files within a symlinked path
        debug(' skipping linked directory %s ...\n' % dest_dir)
        return

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for f in src_files:
        fn = os.path.basename(f)
        dest_file = os.path.join(dest_dir, fn)

        if os.path.exists(dest_file) and not replace:
            debug(' skipping file %s ...\n' % dest_file)
            continue

        if os.path.islink(dest_file):
            debug(' unlinking %s ...\n' % dest_file)
            os.unlink(dest_file)
        elif os.path.exists(dest_file):
            debug(' removing %s ...\n' % dest_file)
            os.unlink(dest_file)

        if symlink:
            debug(' linking %s --> %s\n' % (f, dest_file))
            os.symlink(f, dest_file)
        else:
            debug(' copying %s --> %s\n' % (f, dest_file))
            shutil.copy(f, dest_file)


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
        for path, dirs, files in os.walk(root):
            for i, d in enumerate(dirs):
                if d in ignore_list:
                    dirs.pop(i)

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
