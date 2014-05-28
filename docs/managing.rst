Managing the server
===================

The Application Framework server can be run in two different
modes, using the built-in development server, or a more
robust production-ready server such as Apache or Nginx.

For many purposes, the development server will be fine, when
deploying to a dedicated server for use by more than one person
at a time, Apache will be more appropriate.  See below for more
information about both deployments

Development server
------------------

As described under `Creating a new project`, a file called `manage.py` has
been linked inside your project folder.  Executing this file will
present a large number of subcommands available for performing maintenace
and development with the server.  The one we are considering is called
``runserver``.  See below for example help output:

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


Apache or nginx
---------------

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
^^^^^^^^^^^^^^

The example configs setup a server using unencrypted HTTP, which is usually
fine for development purposes.  For deployed instances, HTTPS would be a more 
appropriate choice.  The Apache example config includes a commented out section 
for setting up an HTTPS virtual server in place of default HTTP.

In addition to the config setup, a certificate will need to be installed in the
server.  A self-signed cert can be used in most cases, or a company cert
could be installed as well.  Check with your local IT department on what
procedures are appropriate for securing and signing your server.
