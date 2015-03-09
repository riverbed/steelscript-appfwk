Steps to run tests:

1) In virtualenv, pip install selenium

2) Create a new appfwk project.  In local_settings file, add the following
parameters.  For TEST_DEVICES, ensure that both a NetProfiler and NetShark
are defined or else the tests cannot complete successfully:

.. code:: python

    INSTALLED_APPS += ('steelscript.appfwk.apps.ui_tests',)
    TEST_DEVICES = [
        {
            'name': 'profiler',
            'module': 'netprofiler',
            'host': '<netprofiler-host-name>',
            'port': 443,
            'username': '<username>',
            'password': '<password>',
        },
        {
            'name': 'shark',
            'module': 'netshark',
            'host': '<netshark-host-name>',
            'port': 443,
            'username': '<username>',
            'password': '<password>',
        }
    ]
    TEST_USER_TIMEZONE = 'US/Eastern'

3) In the project directory, run the tests like so:

.. code:: bash

    $ python manage.py test ui_tests


