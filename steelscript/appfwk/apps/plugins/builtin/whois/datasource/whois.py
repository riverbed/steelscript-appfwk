from steelscript.appfwk.apps.datasource.modules.analysis import \
     AnalysisTable, AnalysisQuery

class WhoisTable(AnalysisTable):
    class Meta:
        proxy = True

    _query_class = 'WhoisQuery'

    def post_process_table(self, field_options):
        super(WhoisTable, self).post_process_table(field_options)
        self.copy_columns(self.options.tables['t'])
        self.add_column('whois', label="Whois link", datatype='html')


def make_whois_link(ip):
    return ('<a href="http://whois.arin.net/rest/nets;q=%s?showDetails=true&'
            'showARIN=false&ext=netref2" target="_blank">Whois record</a>' % ip)

class WhoisQuery(AnalysisQuery):

    def post_run(self):
        """ Return a data frame that simply adds a whois link for each IP. """
        df = self.tables['t']
        df['whois'] = df['host_ip'].map(make_whois_link)
        self.data = df
        return True
