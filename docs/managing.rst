Managing the server
===================

The Application Framework server can be run in two different
modes, using the built-in development server, or a more
robust production-ready server such as Apache or Nginx.

For many purposes, the development server will be fine, when
deploying to a dedicated server for use by more than one person
at a time, Apache will be more appropriate.  See :ref:`Running the server`
below for more information about both deployments.

Maintenance / Rebuilding
------------------------

Several commands support ongoing maintenance of the App Framework server,
useful during development, debugging, or upgrading.


.. _collecting reports:

Collecting Reports
^^^^^^^^^^^^^^^^^^

When a new App Framework project gets created, all the available
example and default reports are copied to the :ref:`reports directory <directory layout>`.
These reports can be updated, or deleted freely, and can be restored
using the ``collectreports`` command:


.. code-block:: console

    $ python manage.py collectreports --help
    Usage: manage.py collectreports [options] None

    Collects reports into App Framework project.

    Options:
      -v VERBOSITY, --verbosity=VERBOSITY
                            Verbosity level; 0=minimal output, 1=normal output,
                            2=verbose output, 3=very verbose output
      --settings=SETTINGS   The Python path to a settings module, e.g.
                            "myproject.settings.main". If this isn't provided, the
                            DJANGO_SETTINGS_MODULE environment variable will be
                            used.
      --pythonpath=PYTHONPATH
                            A directory to add to the Python path, e.g.
                            "/home/djangoprojects/myproject".
      --traceback           Print traceback on exception
      --overwrite           Overwrite ALL existing reports.
      --version             show program's version number and exit
      -h, --help            show this help message and exit

When adding a new package, or plugin to the system, this command should be
run to copy over any new example reports included.

Use the ``overwrite`` option carefully, this will overwrite any changes
you have made to the reports in your folder.

.. _reloading reports:

Reloading Reports
^^^^^^^^^^^^^^^^^^

With any new changes made to the reports in your :ref:`reports directory <directory layout>`
you will want to get those changes recognized by the system.  The most useful
way is to use the ``Reload This Report`` or ``Reload All Reports`` from the
upper-right dropdown menu in the browser, but there is also a command-line
option available too:

.. code-block:: console

    $ python manage.py reload --help
    Usage: manage.py reload [options] None

    Reloads the configuration defined in the config directory

    Options:
      -v VERBOSITY, --verbosity=VERBOSITY
                            Verbosity level; 0=minimal output, 1=normal output,
                            2=verbose output, 3=very verbose output
      --settings=SETTINGS   The Python path to a settings module, e.g.
                            "myproject.settings.main". If this isn't provided, the
                            DJANGO_SETTINGS_MODULE environment variable will be
                            used.
      --pythonpath=PYTHONPATH
                            A directory to add to the Python path, e.g.
                            "/home/djangoprojects/myproject".
      --traceback           Print traceback on exception
      --report-id=REPORT_ID
                            Reload single report.
      --report-name=REPORT_NAME
                            Reload single report by fully qualified name.
      --report-dir=REPORT_DIR
                            Reload reports from this directory.
      --namespace=NAMESPACE
                            Reload reports under this namespace.
      --version             show program's version number and exit
      -h, --help            show this help message and exit

.. _collecting logs:

Collecting Logs
^^^^^^^^^^^^^^^

In cases where a problem occurs, the logfiles usually provide a good
indicator of the root cause.  A built-in command helps collect these
files for distribution to the developers or for posting to mailing lists
or archiving:

.. code-block:: console

    $ python manage.py collect_logs --help
    Usage: manage.py collect_logs [options] None

    Collects log files and system info and creates file `debug-<timestamp>.zip`

    Options:
        <truncated>

.. _reset appfwk:

Resetting App Framework Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When wishing to start from a clean slate, the command ``reset_appfwk`` can
be used to clear the database, caches, and logs then re-initialize everything.

A helpful warning will be presented (unless skipped with the ``--force``
option) as a reminder that this will completely delete the database!  Though
the warning is dire, there are only a few items which will be irretrieveably
lost, and there are workarounds for users and devices:

    * users
    * devices
    * locations
    * admin preferences
    * caches, including job history

For users, by default the server will attempt to store the user table offline
before resetting the database, and then restore it afterwards.  This can
be skipped via the ``--drop-users`` option which will result in all users
being deleted with only the default admin user remaining.

For devices, each time a new device gets added or updated during normal system
use, a local cache gets created with all the info minus the password, so the
primary inconvenience here requires all passwords to be re-entered after a
reset.

Reports and their defined tables will be re-created as part of the reload
process.

.. code-block:: console

    $ python manage.py reset_appfwk --help
    Usage: manage.py reset_appfwk [options] None

    Reset the database. Prompts for confirmation unless `--force` is included as an argument.

    Options:
      -v VERBOSITY, --verbosity=VERBOSITY
                            Verbosity level; 0=minimal output, 1=normal output,
                            2=verbose output, 3=very verbose output
      --settings=SETTINGS   The Python path to a settings module, e.g.
                            "myproject.settings.main". If this isn't provided, the
                            DJANGO_SETTINGS_MODULE environment variable will be
                            used.
      --pythonpath=PYTHONPATH
                            A directory to add to the Python path, e.g.
                            "/home/djangoprojects/myproject".
      --traceback           Print traceback on exception
      --force               Ignore reset confirmation.
      --drop-users          Drop all locally created users, only default admin
                            account will be enabled afterwards. Default will keep
                            all user accounts across reset.
      --version             show program's version number and exit
      -h, --help            show this help message and exit


.. _Running the server:

Running the server
------------------

As decribed above, the server can be run in one of two modes :ref:`development`
and :ref:`production` via sofware like Apache, or nginx.

.. _development:

Development server
^^^^^^^^^^^^^^^^^^

As described under :ref:`creating a new project`, a file called
:ref:`manage.py <directory layout>` has been linked inside your project folder.
Executing this file will present a large number of subcommands available for
performing maintenace and development with the server.  The one we are
considering is called ``runserver``.  See below for example help output:

.. code-block:: console

    $ python manage.py runserver -h
    Usage: manage.py runserver [options] [optional port number, or ipaddr:port]

    Starts a lightweight Web server for development and also serves static files.

    Options:
      -v VERBOSITY, --verbosity=VERBOSITY
                            Verbosity level; 0=minimal output, 1=normal output,
                            2=verbose output, 3=very verbose output
      --settings=SETTINGS   The Python path to a settings module, e.g.
                            "myproject.settings.main". If this isn't provided, the
                            DJANGO_SETTINGS_MODULE environment variable will be
                            used.
      --pythonpath=PYTHONPATH
                            A directory to add to the Python path, e.g.
                            "/home/djangoprojects/myproject".
      --traceback           Print traceback on exception
      -6, --ipv6            Tells Django to use a IPv6 address.
      --nothreading         Tells Django to NOT use threading.
      --noreload            Tells Django to NOT use the auto-reloader.
      --nostatic            Tells Django to NOT automatically serve static files
                            at STATIC_URL.
      --insecure            Allows serving static files even if DEBUG is False.
      --version             show program's version number and exit
      -h, --help            show this help message and exit

In its simplest form, just executing ``python manage.py runserver`` will start
a development server on your local machine at port 8000.  The port can
be overridden, and if you want the server to be accessible to external hosts
(because you are running it inside a virtual machine, for instance), then
pass your explicit ip address and port number.  For example, on many Linux
machines the application ``facter`` is available which can present many
basic facts about the host.  Using this command would be like so:

.. code-block:: console

    $ python manage.py runserver `facter ipaddress`:8000

More detailed discussion and explanation of the settings can be found
in the `official Django documentation <https://docs.djangoproject.com/en/1.5/ref/django-admin/#runserver-port-or-address-port>`_.


.. _production:

Production server
^^^^^^^^^^^^^^^^^

Both `Apache <http://apache.org>`_ and `nginx <http://nginx.org>`_ can be used
to serve App Framework in a dedicated server environment.  Example configurations
for each type of service are included in the ``example-configs`` folder:

* ``example-configs/apache2.conf`` - example for Apache2 virtual server
* ``example-configs/nginx.conf`` - example for nginx server

The Apache configuration assumes that ``mod_wsgi`` is enabled for use, more
details on configuration under this approach can be found within the
`mod_wsgi documentation <https://code.google.com/p/modwsgi/wiki/InstallationInstructions>`_.

The nginx configuration primarily provides static media delivery and routes
requests to a WSGI server such as `gunicorn <gunicorn.org>`_.  gunicorn's
`deployment page <http://gunicorn.org/#deployment>`_ has more detailed guidelines
that may be helpful.

Enabling HTTPS
**************

The example configs setup a server using unencrypted HTTP, which is usually
fine for development purposes.  For deployed instances, HTTPS would be a more
appropriate choice.  The Apache example config includes a commented out section
for setting up an HTTPS virtual server in place of default HTTP.

In addition to the config setup, a certificate will need to be installed in the
server.  A self-signed cert can be used in most cases, or a company cert
could be installed as well.  Check with your local IT department on what
procedures are appropriate for securing and signing your server.
