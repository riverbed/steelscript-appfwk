#!/usr/bin/env python

# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import os
import sys
import imp
from os.path import dirname, abspath


# Django's process for finding management commands doesn't support
# namespaced packages like steelcript.*.  The function below comes
# from an outstanding pull request, and monkey patches the core
# django code at runtime.  Replace this as needed when moving to
# future django releases.

# Core django bug: https://code.djangoproject.com/ticket/14087
# links to pull request https://github.com/django/django/pull/178
# using specific patch:
#   https://github.com/django/django/commit/82f5a71
def find_management_module(app_name):
    """
    Determines the path to the management module for the given app_name,
    without actually importing the application or the management module.

    Raises ImportError if the management module cannot be found for any reason.
    """
    parts = app_name.split('.')
    parts.append('management')

    for i in range(len(parts), 0, -1):
        try:
            path = sys.modules['.'.join(parts[:i])].__path__
        except AttributeError:
            raise ImportError("No package named %s" % parts[i-1])
        except KeyError:
            continue

        parts = parts[i:]
        parts.reverse()
        break
    else:
        parts.reverse()
        part = parts.pop()
        path = sys.path

        # When using manage.py, the project module is added to the path,
        # loaded, then removed from the path. This means that
        # testproject.testapp.models can be loaded in future, even if
        # testproject isn't in the path. When looking for the management
        # module, we need look for the case where the project name is part
        # of the app_name but the project directory itself isn't on the path.
        try:
            next_path = []
            for p in path:
                try:
                    next_path.append(imp.find_module(part, [p])[1])
                except ImportError:
                    pass
            if not next_path:
                raise ImportError("No module named %s" % part)
            path = next_path
        except ImportError as e:
            if os.path.basename(os.getcwd()) != part:
                raise e

    while parts:
        part = parts.pop()
        next_path = []
        for p in path:
            try:
                next_path.append(imp.find_module(part, [p])[1])
            except ImportError:
                pass
        if not next_path:
            raise ImportError("No module named %s" % part)
        path = next_path

    return path[0]

import django.core.management
django.core.management.find_management_module = find_management_module


if __name__ == "__main__":
    # Add the parent directory of 'manage.py' to the python path, so
    # manage.py can be run from any directory.
    # From http://www.djangosnippets.org/snippets/281/
    sys.path.insert(0, dirname(dirname(abspath(__file__))))
    sys.path.insert(0, os.getcwd())

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "local_settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
