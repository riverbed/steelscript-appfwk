Projects
======================

.. _creating a new project:

Creating a new project
----------------------

New Application Framework projects can be created at any time using
the sequence of steel subcommands, ``steel appfwk mkproject``, and
``steel appfwk init``.

First create a new project directory using ``steel appfwk mkproject``.  The
options include:

.. code-block:: console

   $ steel appfwk mkproject -h
   Usage: steel appfwk mkproject [options]

   Install new local App Framework project

   Options:
     --version          show program's version number and exit
     -h, --help         show this help message and exit
     -d DIR, --dir=DIR  Optional path for new project location
     -v, --verbose      Extra verbose output

With no options or arguments, you will be prompted for a directory to
create your new project in, with the default name of ``appfwk_project``.
Feel free to choose any name you'd like - there is no limit on the number of
projects you can create, for instance you could have one for development, and one
for demonstrations.

.. code-block:: console

    $ steel appfwk mkproject
    Generating new Application Framework project ...

    Enter absolute path for project files [/tmp/appfwk_project]: /tmp/demo_project
    Creating project directory /tmp/demo_project ...
    Writing local settings /tmp/demo_project/local_settings.py ... done.

    *****

    App Framework project created.
    Change to that directory and run 'steel appfwk init' to initialize the project.

Once the project has been created, several new folders, files and symlinks will
be located there, which we will go over in the next section.  To start, just
initialize the project using the default settings, and the new project will
be ready for use!

.. code-block:: console

    $ steel appfwk init
    Initializing project using default settings....done


.. _directory layout:

Directory layout
----------------

With the a new project created and initialized, the following items should
be present:

.. code-block:: console

    - manage.py <symlink>
    - reports
    - local_settings.py
    - logs
    - data
    - example-configs
    - media <symlink>
    - thirdparty <symlink>

Lets discuss in order listed above:

* ``manage.py`` - symlink to the 'manage.py' script from the installation package.
  This command provides an interface to detailed project maintenance operations,
  as well as helpful development and debugging tools.  Execute
  'python manage.py -h' to see an exhaustive list of available subcommands,
  but those which are most helpful to use for App Framework are discussed
  in this documentation.

* ``reports`` - contains a few sample reports to get started with.  See
  `reports` for detailed walk through of how reports are defined.

* ``local_settings.py`` - the project settings file, covered in more detail
  under `Configuration`.  The database, logging, and other project configuration
  gets handled via this file.

* ``logs`` - App Framework runtime logs are stored here, under log.txt and
  log-db.txt.  Both logs provide very detailed debug level logging, and are
  typically the first place to look when trying to debug a particular problem.

* ``data`` - contains the default sqlite database, along with subdirectories
  'datacache' and 'initial_data', that store project specific transient data.

* ``example-configs`` - contains example configuration files for Apache, and nginx,
  as well as some sample LDAP settings that can be added to the local_settings.py
  file.  Two example geolocation files are also included here to provide
  templates for your own location setups.

* ``media`` and ``thirdparty`` - images, javascript libraries, and css files
  are stored here.



