class SyncTask(object):
    def __init__(self, job, queryclass):
        self.job = job
        self.queryclass = queryclass

    def __unicode__(self):
        return "<SyncTask %s>" % (self.job)

    def __str__(self):
        return "<SyncTask %s>" % (self.job)

    def __repr__(self):
        return unicode(self)

    def start(self):
        self.do_run()
