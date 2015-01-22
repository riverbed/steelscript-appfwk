# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


from steelscript.appfwk.apps.datasource.modules.analysis import \
    AnalysisTable, AnalysisQuery


# Common translation function
def make_whois_link(ip):
    s = ('<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&'
         'showARIN=false&ext=netref2" target="_blank">Whois record</a>' % ip)
    return s


#
# Custom Analysis classes for creating Whois table
#
class WhoisTable(AnalysisTable):
    class Meta:
        proxy = True

    _query_class = 'WhoisQuery'

    def post_process_table(self, field_options):
        super(WhoisTable, self).post_process_table(field_options)
        self.copy_columns(self.options.tables['t'])
        self.add_column('whois', label="Whois link", datatype='html')


class WhoisQuery(AnalysisQuery):

    def post_run(self):
        """ Return a data frame that simply adds a whois link for each IP. """
        df = self.tables['t']
        df['whois'] = df['host_ip'].map(make_whois_link)
        self.data = df
        return True


#
# Single Analysis Function for doing the same thing as above, but with
# less flexibility for table definitions
#
def whois_function(query, tables, criteria, params):
    # we want the first table, don't care what its been named
    t = query.tables.values()[0]
    t['whois'] = t['host_ip'].map(make_whois_link)
    return t
