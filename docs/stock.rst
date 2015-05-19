Writing a Plugin
================

This tutorial presents a step-by-step description of how to develop a
steelscript appfwk plugin. No tutorial can be as useful as an example.
Therefore, in this tutorial, a steelscript-stock plugin is used to explain
the process of how to construct steelscript appfwk plugin. Note that
the stock data is fetched from yahoo finance API as a thrid party resource.
By changing the data source as well as modify the reports, appfwk plugin
can be used to display data from almost any where, such as a csv file, a
rest API or a device with reporting capability, etc.

Creating the skeleton of a plugin
---------------------

First we need to run the command ``steel appfwk mkplugin`` in a shell:

.. code-block:: python

   $ cd /tmp
   $ steel appfwk mkplugin
   Give a simple name for your plugin (a-z, 0-9, _): stock
   Give your plugin a title []: Steelscript Stock
   Briefly describe your plugin []: Steelscript Stock Appfwk plugin
   Author's name []: author
   Author's email []: email
   Writing:  /private/tmp/steelscript-stock/LICENSE
   Writing:  /private/tmp/steelscript-stock/MANIFEST.in
   Writing:  /private/tmp/steelscript-stock/README.rst
   Writing:  /private/tmp/steelscript-stock/setup.py
   Writing:  /private/tmp/steelscript-stock/gitpy_versioning/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/admin.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/models.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/plugin.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/datasources/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/datasources/stock_source.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/devices/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/devices/stock_device.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/libs/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/reports/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/appfwk/reports/stock_report.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/commands/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/commands/README.rst
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/commands/subcommand.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/core/__init__.py
   Writing:  /private/tmp/steelscript-stock/steelscript/stock/core/README.rst
   Checking if git is installed...done
   Initializing project as git repo...done
   Creating initial git commit...done
   Tagging as release 0.0.1...done


Installing from source
----------------------
Once you have created the source tree of you plugin, you need to install it as below.

.. code-block:: bash

   $ cd steelscript-stock
   $ pip install -e .

Details about installing steelscript plugin can be found
:ref:`Installing a plugin <installing a plugin>`.

.. _Data fetch API:

Developing data fetch API
--------------------------------
You need to develop an API to fetch data to feed the appfwk engine. This step is recommended
to be done early as we can understand better the data format, which would help define the
structure of the appfwk reports later.

First we need to create a python module app.py in steelscript/stock/core directory. The reason
the module app.py resides in core directory instead of appfwk directory is that the API can
be used independently without appfwk. Below shows how a stock data API might look like.

.. code-block:: python

    import urllib

    # Mapping from price measure to the relative position
    # in the response string
    mapping = {'open': 1,
               'high': 2,
               'low': 3,
               'close': 4,
               'volume': 5}
    
    class StockApiException(Exception):
        pass
    
    def get_historical_prices(begin, end, symbol, measures,
                              resolution='1 day'):
        """Get historical prices for the given ticker symbol.
        Returns a list of dicts keyed by 'date' and measures
    
        :param string begin: begin date of the inquire interval
        :param string end: end date of the inquire interval
        :param string symbol: symbol of one stock to query
        :param list measures: a list of prices that needs to be queried,
        should be a subset of ["open", "high", "low", "close", "volume"]
        :param string resolution: '1 day' or '5 days'
        :param boolean date_obj: dates are converted to datetime objects
        from date strings if True. Otherwise, dates are stored as strings
        """
        try:
            reso = 'w' if str(resolution)[0:6] == '5 days' else 'd'
            url = ('http://ichart.finance.yahoo.com/table.csv?s=%s&' % symbol +
                   'a=%s&' % str(int(begin[5:7]) - 1) +
                   'b=%s&' % str(int(begin[8:10])) +
                   'c=%s&' % str(int(begin[0:4])) +
                   'd=%s&' % str(int(end[5:7]) - 1) +
                   'e=%s&' % str(int(end[8:10])) +
                   'f=%s&' % str(int(end[0:4])) +
                   'g=%s&' % reso +
                   'ignore=.csv')
            ret = []
            days = urllib.urlopen(url).readlines()
            for day in reversed(days[1:]):
                day = day[:-2].split(',')
                date = day[0]
                daily_prices = {'date': date}
                for m in measures:
                    if m in mapping:
                        daily_prices[m] = float(day[mapping[m]])
                ret.append(daily_prices)
        except:
            raise StockApiException("Symbol '%s' is invalid or Stock '%s' was"
                                    " not on market on %s" % (symbol, symbol,
                                                              end))
        return ret

The above function get_historical_prices leverages the yahoo stock api to get the
daily transaction volumes as well as daily prices (including high, low, open and close)
for a stock within a date range. The return date format is a list of python dicts, with
each dict represent the data of the stock for one day.

.. code-block:: python

    >>> from steelscript.stock.core.app import get_historical_prices
    >>> from pprint import pprint
    >>> pprint(get_historical_prices(begin='2015-04-01', end='2015-04-05', symbol='rvbd', measures=['open','close', 'high', 'low','volume']))
    [{'close': 20.92,
      'date': '2015-04-01',
      'high': 20.92,
      'low': 20.9,
      'open': 20.91,
      'volume': 1754900.0},
     {'close': 20.92,
      'date': '2015-04-02',
      'high': 20.94,
      'low': 20.9,
      'open': 20.91,
      'volume': 1851400.0},
     {'close': 20.92,
      'date': '2015-04-03',
      'high': 20.92,
      'low': 20.92,
      'open': 20.92,
      'volume': 0.0}]

Creating appfwk reports
-----------------------
From the above API, we can see that in order to generate stock data, we need to pass in
parameters, including stock symbol, start date, end date, the price names, resolution.
The returned data can have information such as dates, daily (include open, close
high, low) prices, and daily transaction volumes. Understanding the data format, one
can set out to define the report to be created. In order to render the desired reports,
we need to define the data source first, which defines criteria required for the report to run.
More importantly, the ``stock_source.py`` also defines ``StockQuery`` class to use
criteria values to derive the stock data by leveraging the :ref:`data fetch API<Data fetch API>`.
At the end we need write the report using defined data sources
to render the data. For illustrative purpose, let us build a simple report that can
show the close price of a stock given a range of dates.

Writing data source
^^^^^^^^^^^^^^^^^^^
As obvious, the generated stock_source.py has included some skeleton code, including
the declaration of the ``StockColumn`` class, the ``StockTable`` class and the ``TableQuery`` class.
For normal reports, there is no need to modify the ``StockColumn`` class. We need to
modify the ``StockTable`` class in order to add criteria, which maps to the parameters passed
to the data fetch API. Details are shown below.

.. code-block:: python

    from steelscript.stock.core.app import get_historical_prices
    from steelscript.appfwk.apps.datasource.models import TableField
    from steelscript.appfwk.apps.datasource.forms import DateTimeField, ReportSplitDateWidget
    from steelscript.appfwk.apps.datasource.models import TableField, TableQueryBase, DatasourceTable, Column
    class StockTable(DatasourceTable):
        class Meta:
            proxy = True
    
        _column_class = 'StockColumn'
        FIELD_OPTIONS = {'duration': '4w',
                         'durations': ('4w', '12w', '24w', '52w', '260w', '520w'),
                         'resolution': '1d',
                         'resolutions': ('1d', '5d')
                         }
    
        def post_process_table(self, field_options):
            # Add a time selection field
            fields_add_time_selection(self, show_end=False,
                                      initial_duration=field_options['duration'],
                                      durations=field_options['durations'])
    
            # Add time resolution selection
            fields_add_resolution(self,
                                  initial=field_options['resolution'],
                                  resolutions=field_options['resolutions'])
    
            # Add end date field
            self.fields_add_end_date('end_date', 'now-0')
            
            # Add stock symbol field
            self.fields_add_stock_symbol()
    
        def fields_add_stock_symbol(self, help_text, keyword='stock_symbol',
                                    initial=None):
            field = TableField(keyword=keyword,
                               label='Stock Symbol',
                               help_text=(help_text),
                               initial=initial,
                               required=True)
            field.save()
            self.fields.add(field)
    
        def fields_add_end_date(self, keyword, initial_end_date):
            field = TableField(keyword=keyword,
                               label='End Date',
                               field_cls=DateTimeField,
                               field_kwargs={'widget': ReportSplitDateWidget,
                                             'widget_attrs': {'initial_date':
                                                              initial_end_date}},
                               required=False)
            field.save()
            self.fields.add(field)


From the above, it can be seen that the function ``post_process_table`` in the ``StockTable`` class
defines the criteria fields. There are four fields added, including duration, end date, stock symbol
and resolution (the start date can be figured out using end date and duration). The values of
duration and resolution are limited to a few.

After the ``StockTable`` class, we need to define the ``run`` method in ``StockQuery`` class,
which is about using the values from the criteria fields in the ``StockTable`` class to derive
the data by leveraging the :ref:`data fetch API <Data fetch API>`. Details as below.

.. code-block:: python

    class TableQuery(TableQueryBase):
    
        def __init__(self, table, job):
            self.table = table
            self.job = job
    
        def run(self):
            criteria = self.job.criteria
        
            # Time selection is available via criterai.starttime and endtime.
            # These are date time strings in the format of YYYY-MM-DD
            self.t0 = str(criteria.end_date - criteria.duration)[:10]
            self.t1 = str(criteria.end_date)[:10]
        
            # Time resolution is a timedelta object
            self.resolution = criteria.resolution
        
            # stock symbol string (can have multiple symbol)
            self.symbol = criteria.stock_symbol
        
            # Dict storing stock prices/volumes according to specific report
            self.data = get_historical_prices(begin=self.t0, end=self.t1, symbol=self.symbol,
                                              measures=['close'], resolution=self.resolution)
                                
            return True


Writing Reports
^^^^^^^^^^^^^^^
After finishing off writing data sources, finally it is time to collect results.
In reports/stock_report.py, we first need to define a report and create a section asscociated with it. 

.. code-block:: python

    from steelscript.appfwk.apps.report.models import Report
    report = Report.create("Stock Report-Multiple Stocks")
    report.add_section()

Next step is to instantiate the ``StockTable`` class and adding columns to the table object after.

.. code-block:: python

    import steelscript.stock.appfwk.datasources.stock_source as stock
    table = stock.StockTable.create(name='stock-close-price',
                                    duration='52w', resolution='1d')
    # Add columns for time and 3 stock columns
    table.add_column('date', 'Date', datatype='time', iskey=True)
    table.add_column('close', 'Close Price')

.. note::
    When creating the stock table object, the passed-in duration and resolution values need to be
    one of the few options listed in ``FIELD_OPTIONS`` in ``StockTable`` class. When adding columns to the
    table, the first parameter, representing the name of the column, needs to be one the keys in the dict
    returned by the :ref:`Data fetch API<Data fetch API>`. For time columns, the ``datatype`` parameter
    needs to be 'time'. Since we plan to plot the data against the dates, thus the ``date`` column needs to
    be specified as the key column, as done by setting ``iskey=True``.

Last step is to add a widget to the report and bind the table to the widget at the same time.

.. code-block:: python

    # Bind the table to a widget for display
    import steelscript.appfwk.apps.report.modules.yui3 as yui3
    report.add_widget(yui3.TimeSeriesWidget, table, 'Close Price', width=12, daily=True)

.. note::
    since the report is a plot based on time, we use yui3.TimeSeriesWidget as the
    widget class. Setting ``width=12`` would span the widget across the whole browser, as the whole browser
    has 12 'columns'. The lables of the obtained plot on the horizontal axis would be in dates if ``daily=True``,
    otherwise the labels would include minutes and seconds.









