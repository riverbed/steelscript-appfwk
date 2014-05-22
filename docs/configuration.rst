Configuration
=============

Once a project has been created (see :doc:`projects`), a *local_settings.py*
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


Using LDAP for Authentication
-----------------------------


Devices
-------


Locations
---------


