Tables
======

All data in the application framework is associated with a Table.
Fundamentally, a Table is a Django model instance that defines the
columns and attributes.  In many senses that Table definition is
similar to a SQL TABLE construct.

Overview
--------

Tables are defined as part of report configuration source files.  All
tables are defined by instantiating a subclass of ``DatasourceTable``
that is specific to a particular data source.

Defining tables involves the following definitions:

**Tables**

    Tables are the fundamental mechanism for defining the data that is
    to collected.  Each table is a specific to a data source and is
    tied to a function in that data source to generate data based on
    the table's columns as well as any static and dynamic criteria.

**Columns**

    A table is fundamentally a two dimensional construct of rows and
    columns.  The report configuration source file defines the columns
    associated with a table.  The column binds a label and data type
    to data source specific fields that the table query function uses
    to populate data.  Similar to a SQL table, some columns are key
    columns, the rest are data or metrics columns.

**Table Fields**

    Table fields define the required and optional criteria associated
    with a table.  Each data source can define a set of table fields
    that are required or optional for each type of table

Note that while tables are defined in the context of a report
configuration source file, tables are only loosely coupled with a
report via widgets.  In fact, it is possible to run tables at the
command line without running an entire report.

Sample Table Definition
~~~~~~~~~~~~~~~~~~~~~~~

The following table is taken from the Wave sample plugin:

.. code-block:: python

   import steelscript.wave.appfwk.datasources.wave_source as wave

   # Define a waves table with 3 separate waves.
   table = wave.WaveTable.create(
       name='wave-table', duration='15min', resolution='1s', beta=4)

   # Add columns for time and the related waves
   table.add_column('time', 'Time', datatype=Column.DATATYPE_TIME, iskey=True)
   table.add_column('sin1', 'Sine Wave 1', func='sin', period='5min', alpha=3)
   table.add_column('sin2', 'Sine Wave 2', func='sin', period='8min', alpha=5)
   table.add_column('cos',  'Cosine Wave', func='cos', period='3min', alpha=2.5)

Creating Tables
---------------

.. currentmodule:: steelscript.appfwk.apps.datasource.models

Table objects are Django model instances backed by the database.
Tables are created by calling the ``create`` class method of specific
table of interest.  Each table type is programmed to generate data
differently.

The term "data source" is intentionally vague, as all that is required
of a given type of table is that it can, on demand, produce a
data set -- a two dimensional set of rows and columns that match
the requested table configuration (options and columns) as well as
dynamic user provided criteria.  The following are some examples of
valid data sources:

* leverage configured devices to run queries on remote machines
* generate data based on some algorithm
* read data from a file or database
* merge data from other tables or source and produce a modified table

The following table lists some of the data source tables
available:

============================== =========================================================================
DatasourceTable Subclass Name  Package
============================== =========================================================================
WaveTable                      steelscript.wave.appfwk.datasources.wave_source
AnalysisTable                  steelscript.appfwk.apps.datasource.modules.analysis
HTMLTable                      steelscript.appfwk.apps.datasource.modules.html
SharepointTable                steelscript.appfwk.apps.plugins.builtin.sharepoint.datasources.sharepoint
SolarwindsTable                steelscript.appfwk.apps.plugins.builtin.solarwinds.datasources.solarwinds
NetProfilerTable               steelscript.netprofiler.appfwk.datasources.netprofiler
NetProfilerTimeSeriesTable     steelscript.netprofiler.appfwk.datasources.netprofiler
NetProfilerGroupbyTable        steelscript.netprofiler.appfwk.datasources.netprofiler
NetProfilerDeviceTable         steelscript.netprofiler.appfwk.datasources.netprofiler_devices
NetProfilerTemplateTable       steelscript.netprofiler.appfwk.datasources.netprofiler_template
NetSharkTable                  steelscript.netshark.appfwk.datasources.netshark
WiresharkTable                 steelscript.wireshark.appfwk.datasources.wireshark_source
============================== =========================================================================

Tables are created by calling the ``create`` class method of the
DatasourceTable subclass:

.. code-block:: python

   from <package> import <cls>
   table = <cls>.create(name, [table_options], [field_options])

.. automethod:: DatasourceTable.create

Adding Columns
~~~~~~~~~~~~~~

.. currentmodule:: steelscript.appfwk.apps.datasource.models

Columns define the keys and values of the data set that this table
will collect.  They are added to a table using
:py:meth:`DatasourceTable.add_column`.

When a query is run, the data source associated with a table
inspects the list of key and value columns and generates a
data table matching the requested column set.

.. automethod:: DatasourceTable.add_column

Synthetic Columns
~~~~~~~~~~~~~~~~~

In addition to columnar data generated by a data source, additional
*synthetic* columns may be attached to a table.  Synthetic
columns provide an easy way to perform computations on other
data columns in the same table.

This is best explained by an example based on the WaveTable above:

.. code-block:: python

   table.add_column('sin1', 'Sine Wave 1', func='sin', period='5min', alpha=3)
   table.add_column('sin1-doubled', synthetic=True, compute_expression='2*{sin1}')

The first is a normal column whose data will be provided by
the wave data source.  The second column is a synthetic column
that is simply the 'sin1' column multiplied by 2.

The ``compute_expression`` column keyword defines the operation to
perform:

* Other column values are referenced using the syntax ``{name}``,
  where ``name`` is the name assigned to another column in the same
  table.  Any number of other columns may be referenced

* Standard mathematical operators may be used: ``+``, ``-``, ``*``,
  ``/``, and others.

* ``{name}`` is actually a Python Pandas Series object, and thus
  functions on series data can be leveraged either by methods on the
  series object or by using the full package path:

  * ``{name}.quantile(0.95)`` will compute the 95th percentile for the
    data in column {name}

  * ``pandas.stats.moments.ewma({name}, span=20)`` will compute the
    EWMA (exponential weighted moving average) of the ``{name}``
    column using a span of 20 data points.

For more advanced analysis techniques, see :doc:`analysis`.

Resampling Time Series Tables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When working with time series data, a common operation is to resample
that data:

* Incoming data is at 1 minute resolution, but the output needs to be
  at 5 minute resolution

* Incoming data has erratic non-normalized timestamps, the output
  should be graphed at steady 1 minute resolution

The application framework will automatically resample timeseries data
when the ``resample=True`` at creation.  In addition, there must be
a criteria field named either ``resample_resolution`` or just
``resolution``, which sets the target resample interval.

When resampling, data from multiple rows must be aggregated (each row
represents a timestamp or time interval).  The aggregation operation
is different for different types of data:

* Counted metrics such as "total bytes" involves
  computing the "sum" of all rows covered by the new interval.

* Peak metrics such as "peak network RTT" require computing the "max"
  of all metrics.

Each data column may be set up with a different ``resample_operation``
based.  The default is ``sum``, but this is not always appropriate for
all data types.

Note that when using synthetic columns as describe above, you can
choose to compute the synthetic columns before or after resampling by
setting ``compute_post_resample``.
