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

.. toctree::

   install
   projects
   configuration
   managing
   usingappfwk
   reports
   tables
   plugins
   analysis
   geolocation

* Python Pandas

* Tutorials

  * Creating a Report
  * Writing an AnalysisTable
  * Wave Plugin Tutorial
