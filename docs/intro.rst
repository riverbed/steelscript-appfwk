Introduction
============

The SteelScript Application Framework is a Django application that
provides a web front end to metrics collected from available
datasources.  A primary goal is to focus on extensibility and
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
allows data to be processed in virtually any conceivable way.
The output of the analysis table is just another table.  This can
then be connected to one or more widgets for visualization, or in turn
be inputs to yet another analysis table for further processing.

