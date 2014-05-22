SteelScript Application Framework
=================================

Welcome to the documentation for the SteelScript Application Framework!

This project makes it easy to:

* Build a web front end to your metrics

* Pull metrics from a variety of data sources:

  * NetProfiler
  * NetShark
  * Wireshark
  * Sharepoint
  * Solarwinds

* Add new data sources with minimal code

* Design custom reports

  * mix and match widgets and data
  * define custom criteria

* Custom analysis via Python hooks and Python Pandas

  * compute statistics, pivot tables, merge, sort, resample
    timeseries

* Plugin architecture makes it easy to share modules

Overview
--------

The SteelScript Application Framework is a Django application that
provides a web front end to metrics collected from available
datasources.  A primary goal is to focus on extensibilty and
modularity:

* Data is normalized to Python Pandas DataFrames
* Data sources need not worry about how the data is visualized
* Visualization modules are independent of data source

.. image:: appfwk-arch.png
   :align: center

Getting an application up and running involves the following steps:

1. Installation
2. Database configuration
3. Define a set of devices to query
4. Define one or more reports in Python:

   a. Define the criteria a user must provide for the report
   b. Define data tables and assign columns of keys and values to report on
   c. Connect data tables to UI widgets for rendering

For more advanced use cases, the output of one or more tables can be
fed as input to analysis tables hooked to a Python callback.  This
allows data to be processed in virtually any conceiveable way.
The output of the analysis table is just another table.  This can
then be connected to one or more widgets for visualization, or in turn
be inputs to yet another analysis table for further processing.

Documentation
-------------

* :doc:`install`

  * Using 'steel'
  * Manual install

    * Linux
    * Windows

  * SteelScript VM
  * Upgrade

* :doc:`projects`

  * Creating a new project
  * Directory layout

* :doc:`configuration`

  * Setting up the database
  * Managing users
  * Using LDAP for Authentication
  * Devices
  * Locations

* Managing the server

  * Development server

    * Start/stop
    * Rebuilding

  * Apache

    * Enabling HTTPS

* Using the Application Framework

  * Logging in
  * Running reports

* Reports

  * Reports, Sections and Widgets

    * Available Widgets
    * Report/Section/Widget options

  * Tables and Columns

    * Available tables across all plugins (link to individual plugins?)
    * Standard table/column options
    * Synthetic columns

  * Custom AnalysisTables

  * Custom Criteria with TableFields

* Plugins

  * Installing downloaded plugins
  * Creating a new plugin
  * Tour of the plugin files and directories

    * Core (core)
    * Devices (appfwk/devices)
    * DataSources (appfwk/datasources)
    * Reports (appfwk/reports)
    * Help functions (appfwk/libs)
    * Models (appfwk/models.py)
    * Commands (management and steel)

  * Generating a downloadable package

* Python Pandas

* Tutorials

  * Creating a Report
  * Writing an AnalysisTable
  * Wave Plugin Tutorial
