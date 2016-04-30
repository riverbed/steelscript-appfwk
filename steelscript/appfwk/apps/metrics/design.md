# Collection Metrics App

This app provides and interface to App Framework in order to collect metrics from outside sources.  While
most of the design has so far focused on retrieviing and optionally storing information, there is
a use case to handle metrics and information pushed rather than pulled.  We will suppor this
via an API that receives the data and process it against a pre-defined schema to determine what, if anything,
to do.  

This basic use case:

 * Model definition inside a Plugin outlines what metrics will be received
   * The definitions will consist of subclasses from new core Abstract base class models: Schema, Metric
 * Adding the Plugin to `INSTALLED_APPS` will register the Models in the DB
 * Admin panel will provide interface to the Schema, offering opportunity to override values
 * Updates to these metrics will be handled via /metrics/<schema> endpoint
 * These updates will
   a) overwrite the current value stored for that metric in storage,
   b) optionally write the history to a persistent datastore (future)
 * The latest values will be available via datasource queries
 * The datasource query will first check if overrides have been stored via Admin panel

## Components

* Base Classes

    * Metric

* Plugin classes

    * PluginMetric

    Example

    * USDANetworkMetric(Metric):
        schema = 'usda_network'

        define additional processing methods here

* URL

    /metric/<schema>/

* Views - POST

    * Receive POST at URL
    * Lookup <schema> and find matching Metrics model
        * valid metrics will be rows in this table, with ``name`` as Key
    * Lookup Serializer for given model
        * each model will have its own custom serializer that maps the incoming
          data into the model object
    * Serialize incoming data
        * if successful, continue
        * else raise error
    * Find metric in given Model
        * if not found, raise 404
    * Process metric with Model ``process`` method
        * this will include custom logic related to how to handle the data
        * the base case will be to just overwrite the row
        * more complex operations could include adding / removing items from a
          list, or adjusting only a portion of the row based on the input data,
          say toggling a status value
    * Return appropriate return code


* Views - Datasource

    * Retrieve status from all metrics
    * For each Metric, find if Override in place
    * If Override, return that, otherwise return Metric

