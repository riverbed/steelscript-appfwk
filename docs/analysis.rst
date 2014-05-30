Analysis Tables
===============

.. module:: steelscript.appfwk.apps.datasource.modules.analysis

The :py:class:`AnalyisTable` allows for fully custom data collection
and analysis.

* leverage pre-requisite tables from other data sources as input
* idenify related table definitions for columns and running additional queries
* define custom table fields to allow run-time changes in behaviour by the user

This section will walk you through the
:py:class:`ClippedWaveTable` from the Wave sample plugin.

:py:class:`ClippedWaveTable`
----------------------------

Description:

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

Notice that no columns are defined -- this is because the function
performed by this analysis table is to replicate the same number of
columns as the input.  In some cases it will be necessary to add
columns, but often the output column set is a function of the input
column set.

Defining the ClippedWaveTable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Now let's look at the code behind that last
``ClippedWaveTable.create()`` call above:

.. code-block:: python

   class ClippedWaveTable(AnalysisTable):
       class Meta: proxy = True

       _query_class = 'ClippedWaveQuery'

       FIELD_OPTIONS = { 'min': 2,
                         'max': 7 }

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

Stepping through this in more detial:

.. code-block:: python

   class ClippedWaveTable(AnalysisTable):
       class Meta: proxy = True

All analysis tables must be subclassed from the base
:py:class:`AnalysisTable`.  The next line is a bit of Django
magic that is required to indicate that this is class is a proxy
for the base ``Table`` model.

.. code-block:: python

       _query_class = 'ClippedWaveQuery'

This class method indicates what class will actually implement the
query function when this table is run.  We will run through the
:py:class:`ClippedWaveQuery` below.

The next few lines define default fields values that will be used
for custom fields.

.. code-block:: python

       FIELD_OPTIONS = { 'min': 2,
                         'max': 7 }

The ``process_options`` class method below is called after table
options have been pre-processed but before the table is actually
created.  This is an opportunity to tweak table options, or in this
case verify that the user properly included a ``waves`` input table.

.. code-block:: python

       @classmethod
       def process_options(cls, table_options):
           table_options = super(ClippedWaveTable, cls).process_options(table_options)

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
                             help_text=('Clip all wave forms at this minimum value'),
                             required=False)

           # Add a custom field for 'max'
           TableField.create(obj=self, keyword='max', label='Max value',
                             initial=field_options['max'],
                             help_text=('Clip all wave forms at this maximum value'),
                             required=False)

Again, we must call the parent class' ``post_process_table`` method
first, then we add our two custom fields for ``min`` and ``max``.
Note here taht we set the initial value to ``field_options['min']``.
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
that whatever columsn were provided on input will show up on output as
well.

:py:class:`ClippedWaveQuery`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The final missing piece is the ``ClippedWaveQuery`` which actually
performs the clipping function at run time:

.. code-block:: python

   class ClippedWaveQuery(AnalysisQuery):

       def post_run(self):
           assert('waves' in self.tables)

           # Grab the incoming 'waves' table, which will have already been
           # run prior to this call.  The result is a pandas DataFrame
           waves = self.tables['waves']

           # Index on 'time' -- this allows the next operation to proceed
           # only the remaining columns
           waves = waves.set_index('time')

           # Apply lower and upper limits to all data columns
           criteria = self.job.criteria
           waves = waves.clip(lower=int(criteria.min), upper=int(criteria.max))

           # Reset the index before returning
           waves = waves.reset_index()

           # Save the result and return success
           self.data = waves
           return True

This class is based on :py:class:`AnalysisQuery`.  When the report is
run, the base class will run all necessary input tables and store the
results in ``self.tables``.  This dictionary will have the same labels
as defined above to the ``tables`` argument.  The results here will be
Pandas DataFrames.

User input criteria is accessible via ``self.job.criteria``.  This is
where we get the run time values for ``min`` and ``max`` to use.

On success, the function will save the result in ``self.data`` and
return True.
