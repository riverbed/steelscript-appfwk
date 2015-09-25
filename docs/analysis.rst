Analysis Tables
===============

The ``AnalysisTable`` allows for fully custom data collection
and analysis and provides the following features:

* Ability to leverage pre-requisite tables from other data sources as input
* Identify related table definitions for columns and running additional queries
* Define custom table fields to allow run-time changes in behaviour by the user

This section will first walk you through the
``ClippedWaveTable`` from the Wave sample plugin.
Then the `Whois` plugin is presented to explain another way of how to utilize the
``AnalysisTable`` features of App framework.

.. _clipped wave:

``ClippedWaveTable``
--------------------

The ``ClippedWaveTable`` is an example ``AnalysisTable`` included within the
Wave plugin that takes a base ``WaveTable`` as input and applies some transformations
on the data. These changes include:

* Define criteria fields ``min`` and ``max`` that define the upper and lower
  clipping bounds

* Take a single input table labeled ``waves`` that defines one or more
  time-series data columns (in addition to a ``time`` column)

* For each input wave column, produce an output wave column that is clipped
  at the user defined ``min`` and ``max``

Using the table in a report
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In order to use the clipped table, we need to define an input table:

.. code-block:: python

   table = wave.WaveTable.create(
       name='wave-table', duration='15min', resolution='1s', beta=4)

   table.add_column('time', 'Time', datatype=Column.DATATYPE_TIME, iskey=True)
   table.add_column('sin1', 'Sine Wave 1', func='sin', period='5min', alpha=3)
   table.add_column('sin2', 'Sine Wave 2', func='sin', period='8min', alpha=10)
   table.add_column('cos',  'Cosine Wave', func='cos', period='3min', alpha=2.5)

We now have a new ``WaveTable`` with 3 waves defined stored in the
variable ``table``.   Now we can define our *clipped* version of that
table:

.. code-block:: python

   clipped_table = wave.ClippedWaveTable.create(
       name='clipped-wave-table', tables={'waves': table},
       min=3, max=9)

The ``tables`` argument to the ``create`` method is a dictionary of
input table references.  The label ``waves`` is specified by the
``ClippedWaveTable``.  The labels become important when there are two
or more input tables.

Notice that no columns are defined -- this is because within the function
definition of this table, it already replicates the same columns from the
input table (see the end of the next section for how this gets handled).
In some cases it will be necessary to add columns like you do for normal
App Framework tables. But as shown here, this step can be skipped.

Defining the ClippedWaveTable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now let's look at the code behind that last
``ClippedWaveTable.create()`` call above:

.. code-block:: python

   class ClippedWaveTable(AnalysisTable):
       class Meta:
           proxy = True

       _query_class = 'ClippedWaveQuery'

       FIELD_OPTIONS = {'min': 2,
                        'max': 7}

       @classmethod
       def process_options(cls, table_options):
           table_options = super(ClippedWaveTable, cls).process_options(table_options)

           # Verify that the user defined a 'waves' input table
           tables = table_options['tables']
           if not tables or len(tables) != 1 or 'waves' not in tables:
               raise ValueError("Tables must contain only a dependent table "
                                "named 'waves'")

           return table_options

       def post_process_table(self, field_options):
           super(ClippedWaveTable, self).post_process_table(field_options)

           # Add a custom field for 'min'
           TableField.create(obj=self, keyword='min',  label='Min value',
                             initial=field_options['min'],
                             help_text=('Clip all wave forms at this minimum value'),
                             required=False)

           # Add a custom field for 'max'
           TableField.create(obj=self, keyword='max', label='Max value',
                             initial=field_options['max'],
                             help_text=('Clip all wave forms at this maximum value'),
                             required=False)

           tables = self.options['tables']
           self.copy_columns(tables['waves'])

Stepping through this in more detail:

.. code-block:: python

   class ClippedWaveTable(AnalysisTable):
       class Meta: proxy = True

All analysis tables must be subclassed from the base
``AnalysisTable``.  The next line is a bit of Django
magic that is required to indicate that this is class is a proxy
for the base ``Table`` model.

.. code-block:: python

       _query_class = 'ClippedWaveQuery'

This class method indicates what class will actually implement the
query function when this table is run.  We will run through the
``ClippedWaveQuery`` below.

The next few lines define default fields values that will be used
for custom fields.

.. code-block:: python

       FIELD_OPTIONS = {'min': 2,
                        'max': 7}

The ``process_options`` class method below is called after table
options have been pre-processed but before the table is actually
created.  This is an opportunity to tweak table options, or in this
case verify that the user properly included a ``waves`` input table.

.. code-block:: python

       @classmethod
       def process_options(cls, table_options):
           table_options = (super(ClippedWaveTable, cls).
	                    process_options(table_options))

           # Verify that the user defined a 'waves' input table
           tables = table_options['tables']
           if not tables or len(tables) != 1 or 'waves' not in tables:
               raise ValueError("Tables must contain only a dependent table "
                                "named 'waves'")

           return table_options

Note that this is a class method because the table object has not yet
been created.  In addition we must make sure to call the parent class'
``process_options`` method and return whatever value it returned.

The ``post_process_table`` method is invoked *after* the table has
been created and saved to the database.  This is our chance
to add columns and custom fields:

.. code-block:: python

       def post_process_table(self, field_options):
           super(ClippedWaveTable, self).post_process_table(field_options)

           # Add a custom field for 'min'
           TableField.create(obj=self, keyword='min',  label='Min value',
                             initial=field_options['min'],
                             help_text=('Clip all wave forms at this'
			                ' minimum value'),
                             required=False)

           # Add a custom field for 'max'
           TableField.create(obj=self, keyword='max', label='Max value',
                             initial=field_options['max'],
                             help_text=('Clip all wave forms at this'
			                ' maximum value'),
                             required=False)

Again, we must call the parent class' ``post_process_table`` method
first, then we add our two custom fields for ``min`` and ``max``.
Note here that we set the initial value to ``field_options['min']``.
This will be either the value defined above in the ``FIELD_OPTIONS``
dictionary, or any override specified on the ``create`` line.  Above
in the previous section the table was created with ``min=3``, so that
will be used as the initial value.  Note that the user can still
change the min at run time, this merely specifies the *default* value
of the form control when the report is loaded.

Finally:

.. code-block:: python

           tables = self.options['tables']
           self.copy_columns(tables['waves'])

This copies all columns from the input ``waves`` table.  This ensures
that whatever columns were provided on input will show up on output as
well.

``ClippedWaveQuery``
~~~~~~~~~~~~~~~~~~~~

The final missing piece is the ``ClippedWaveQuery`` which actually
performs the clipping function at run time:

.. code-block:: python

   from steelscript.appfwk.apps.jobs import QueryComplete

   class ClippedWaveQuery(AnalysisQuery):

       def analyze(self, jobs):
           assert('waves' in jobs)

           # Grab the incoming 'waves' table, which will have already been
           # run prior to this call.  The result is a pandas DataFrame
           waves = jobs['waves'].data()

           # Index on 'time' -- this allows the next operation to proceed
           # only the remaining columns
           waves = waves.set_index('time')

           # Apply lower and upper limits to all data columns
           criteria = self.job.criteria
           waves = waves.clip(lower=int(criteria.min), upper=int(criteria.max))

           # Reset the index before returning
           waves = waves.reset_index()

           return QueryComplete(waves)

This class is based on ``AnalysisQuery``.  When the report is
run, the base class will run all necessary input tables and store the
results in ``jobs``.  This dictionary will have the same labels
as defined above to the ``tables`` argument.  The results here will be
Pandas DataFrames.

User input criteria is accessible via ``self.job.criteria``.  This is
where we get the run time values for ``min`` and ``max`` to use.

On success, the function will return ``QueryComplete(waves)``, where
``waves`` is a Pandas DataFrame.

`Whois` Plugin
--------------
The Whois Plugin provides a very simple view into how to utilize
AnalysisTables in the two supported means:

* custom datasource via subclassing AnalysisTable and AnalysisQuery
  (as shown above in section :ref:`ClippedWaveTable <clipped wave>`)

* single python function

In both cases, the analysis function takes an input table with one
column that includes IP addresses, then creates a new column from
that with an HTML link to the whois lookup page on the internet.

This section will go into some details about how to utilize a python
function for analysis purposes.

Define the input table
~~~~~~~~~~~~~~~~~~~~~~

To start off, we need to define an input table in the report module:

.. code-block:: python

   report = Report.create("Whois Example Report", position=1)

   report.add_section()
   table = NetProfilerGroupbyTable.create(
       '5-hosts', groupby='host', duration='1 hour',
       filterexpr='not srv host 10/8 and not srv host 192.168/16'
   )
   table.add_column('host_ip', 'IP Addr', iskey=True, datatype='string')
   table.add_column('avg_bytes', 'Avg Bytes', units='B/s', sortdesc=True)

There is nothing special about this table, except that it includes a column
of IP addresses that will be used as input to our analysis function.
   
Define the analysis function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Next, an analysis function needs to be defined. This is usually done
in the datasource module to facilitate importing. This function builds
the required data based on the data of the input table to be used for the report.

.. code-block:: python

   # Common translation function
   def make_whois_link(ip):
       s = ('<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&'
            'showARIN=false&ext=netref2" target="_blank">Whois record</a>' % ip)
       return s

``make_whois_link`` is a function which will be used by the analysis function
defined below. It takes an IP address as an argument and returns an HTML link to
the whois lookup page on the internet.
       
.. code-block:: python
       
   def whois_function(query, tables, criteria, params):
       # we want the first table, don't care what its been named
       t = query.tables.values()[0]
       t['whois'] = t['host_ip'].map(make_whois_link)
       return t

This ``whois_function`` does all the analysis in place of the AnalysisQuery
we've seen before. When writing your own, you can name it anything you like,
but you will need the same four keyword arguments in your function definition.
They don't all have to be used, as you can see in our example, though.

========= ===============================================================
Arguments 
========= ===============================================================
query     The incoming Job reference, this includes the calculated \ 
          results of all dependant tables.
tables    A dictionary reference to the dependant table definitions. \ 
          These should be used if needing to get to the original tables \
	  in the database.
criteria  A dictionary of all the passed criteria
params    Additional parameters that were defined in the report. \ 
          These can help make the functions more flexible so the same \
	  definition can be used across multiple report types with a \
	  different attribute in each case.
========= =============================================================== 


Inside the ``whois_function``, it is worth mentioning that ``t`` is a pandas
DataFrame, thus you can add the extra ``whois`` column to ``t`` by applying the
mapping function ``make_whois_link`` to ``t['host_ip']``.

Define the columns for report
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
And finally, now that we have our base table defined and our analysis function created,
it is time to create an Analysis table in the report module. Note that we also need to
add columns to the analysis table.

.. code-block:: python

   function_table = AnalysisTable.create('whois-function-table',
                                         tables={'t': table},
                                         function=whois_function)
   function_table.copy_columns(table)
   function_table.add_column('whois', label='Whois link', datatype='html')

   report.add_widget(yui3.TableWidget, function_table,
                     "Analysis Function Link table", width=12)

Note that an extra column ``whois`` is added to the ``function_table``, so that
the report can render all the data returned by the ``whois_function``.

Summary
-------
The two examples demonstrate two different ways to utilize the ``AnalysisTable``
features of App framework.

The `ClippedWaveTable` example uses the extensible **custom table definition**
approach where two new classes are defined to perform the initial table
definition and data processing.

The `Whois` plugin looks much like the first, but uses a **single
function** to perform the data processing.

Both approaches have benefits. The custom definitions allow far more
flexibility in how things get defined, while the function approach can
be simpler for a quick report.
