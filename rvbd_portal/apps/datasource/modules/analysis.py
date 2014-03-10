# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.

import logging

from rvbd.common.jsondict import JsonDict
from rvbd_portal.apps.datasource.datasource import DatasourceTable
from rvbd_portal.apps.datasource.models import Column, Job, Table, BatchJobRunner

logger = logging.getLogger(__name__)


class AnalysisException(Exception):
    def _init__(self, message, *args, **kwargs):
        self.message = message
        super(AnalysisException, self).__init__(*args, **kwargs)


class AnalysisTable(DatasourceTable):
    table_options = {'tables': None,        # required, dict of tables
                     'func': None,          # required, function reference
                     'params': None}

    field_params = {'copy_fields': True}

    def pre_process_table(self):
        # handle direct id's, table references, or table classes
        # from tables option and transform to simple table id value
        for k, v in self.table_options['tables'].iteritems():
            if hasattr(v, 'table'):
                self.table_options['tables'][k] = v.table.id
            else:
                self.table_options['tables'][k] = getattr(v, 'id', v)

    def post_process_table(self):
        if self.field_params['copy_fields']:
            keywords = set()
            for table_id in self.table_options['tables'].values():
                for f in Table.objects.get(id=table_id).fields.all():
                    if f.keyword not in keywords:
                        self.table.fields.add(f)
                        keywords.add(f.keyword)


class TableQuery(object):
    def __init__(self, table, job):
        self.table = table
        self.job = job

    def __unicode__(self):
        return "<AnalysisTable %s>" % self.job

    def __str__(self):
        return "<AnalysisTable %s>" % self.job

    def mark_progress(self, progress):
        # Called by the analysis function
        self.job.mark_progress(70 + (progress * 30)/100)
        
    def run(self):
        # Collect all dependent tables
        options = self.table.options
        logger.debug("%s: dependent tables: %s" % (self, options.tables))
        deptables = options.tables
        depjobids = {}
        batch = BatchJobRunner(self.job, max_progress=70)
        for name, id in deptables.items():
            id = int(id)
            deptable = Table.objects.get(id=id)
            job = Job.create(
                table=deptable,
                criteria=self.job.criteria.build_for_table(deptable)
            )
            batch.add_job(job)
            logger.debug("%s: starting dependent job %s" % (self, job))
            depjobids[name] = job.id
                    
        batch.run()

        logger.debug("%s: All dependent jobs complete, collecting data"
                     % str(self))
        # Create dataframes for all tables
        dfs = {}
        
        failed = False
        for name, id in depjobids.items():
            job = Job.objects.get(id=id)
                
            if job.status == job.ERROR:
                self.job.mark_error("Dependent Job failed: %s" % job.message)
                failed = True
                break
            
            f = job.data()
            dfs[name] = f
            logger.debug("%s: Table[%s] - %d rows" %
                         (self, name, len(f) if f is not None else 0))

        if failed:
            return False

        logger.debug("%s: Calling analysis function %s"
                     % (self, str(options.func)))

        try:
            df = options.func(self, dfs, self.job.criteria,
                              params=options.params)
        except AnalysisException as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.func, e.message))
            logger.exception("%s raised an exception" % self)
            return False
        except Exception as e:
            self.job.mark_error("Analysis function %s failed: %s" %
                                (options.func, str(e)))
            logger.exception("%s: Analysis function %s raised an exception" %
                             (self, options.func))
            return False
            
        # Sort according to the defined sort columns
        if df is not None:
            if self.table.sortcol:
                n = self.table.sortcol.name
                sorted = df.sort(n, ascending=False)
                # Move NaN rows to the end
                df = (sorted[sorted[n].notnull()]
                      .append(sorted[sorted[n].isnull()]))

            if self.table.rows > 0:
                self.data = df[:self.table.rows]
            else:
                self.data = df
        else:
            self.data = None
        
        logger.debug("%s: completed successfully" % (self))
        return True
