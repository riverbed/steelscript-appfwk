Configuration
=============

Once a project has been created (see :doc:`projects`), a ``local_settings.py``
file will be in the directory with default settings available for customization.

Setting up the database
-----------------------

By default, *local_settings.py* uses a simple sqlite database to store
configurations, reports, and other data.  This is fine for single-user
and basic development, but sqlite has concurrancy and performance limitations
which make it unsuitable for more dedicated use.

.. code-block:: python

    DATABASES = {
        'default': {
            # Optionally change 'sqlite3' to 'postgresql_psycopg2', 'mysql' or 'oracle'.
            # for connection to other database engines
            'ENGINE': 'django.db.backends.sqlite3',

            # Path to database file if using sqlite3.
            # Database name for others
            'NAME': os.path.join(DATAHOME, 'data', 'project.db'),

            'USER': '',     # Not used with sqlite3.
            'PASSWORD': '', # Not used with sqlite3.
            'HOST': '',     # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',     # Set to empty string for default. Not used with sqlite3.
        }
    }

More detailed discussion of these parameters can be found in the
`django documentation <https://docs.djangoproject.com/en/1.5/ref/settings/#databases>`_.
If help is needed configuring a MySql or PostgreSQL database, many resources
are available online.

Managing users
--------------

As a default, a single user is enabled on the system with the username /
password combination: ``admin`` / ``admin``.  This account has full administrative
rights and should only be used by trusted users.

The password for this default account can be changed at any time via the
"Change User Password" link under admin->Preferences.

To add additional user accounts or manage existing ones, choose the
"Admin Panel" option from the dropdown menu.  This will lead to page similar to
the following:

.. image:: admin-panel-users.png
   :align: center

You can use the ``Add`` button directly from this page or click on ``Users`` to
manage all locally stored user accounts.

Using LDAP for Authentication
-----------------------------


A file named ``ldap_example.py`` can be found in the directory
``example-configs`` within the app framework project that gets created for you.
This file includes several example settings that can be incorporated into your
``local_settings.py`` file to enabled authentication against an internal LDAP
or Active Directory service.

As noted at the top of the file, two additional python packages are required:

* ldap
* django-auth-ldap

With those installed, further information can be found at the `django-auth-ldap
documentation site <http://pythonhosted.org/django-auth-ldap/authentication.html>`_.

Note that under the ``AUTHENTICATION_BACKENDS`` setting, including both
``LDAPBackend`` and ``ModelBackend`` will still allow locally created user
accounts to access the site.


Devices
-------

After the server is freshly initialized, logging into the server will bring
up the "Edit Devices" page.  This page is only accessible to admin users,
and provides a means to add devices for use throughout the site.

Click on "Add New Device" and fill out the requested information for
each device you'd like to be able to use as a datasource.

Locations
---------

TBD
