# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import sys
import json
import logging
import subprocess
from collections import OrderedDict

from flask import Flask, request
from flask_restful import Resource, Api, abort, fields, marshal_with

import reschema
from reschema.exceptions import ValidationError

#logging.basicConfig(filename='progressd.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app)

# API Service Definitions
service = reschema.ServiceDef()
service.load('progressd.yaml')
job_schema = service.find_resource('job')
jobs_schema = service.find_resource('jobs')


JOBS = {}              # Map of Job IDs to Job objects

PARENT_MIN_PROGRESS = 33    # progress when single child complete
PARENT_MAX_PROGRESS = 90    # max progress until job is complete


def get_job_or_404(job_id):
    if job_id not in JOBS:
        abort(404, message="Job {} not found".format(job_id))
    return JOBS[job_id]


class Job(object):
    """Basic data structure for Job status"""

    def __init__(self, job_id, status, progress,
                 master_id=None, parent_id=None):
        self.job_id = job_id
        self.status = status
        self.progress = progress
        self.master_id = master_id
        self.parent_id = parent_id

        self.update_links()

    def __cmp__(self, other):
        return cmp(self.job_id, other.job_id)

    def values(self):
        return ', '.join('%s: %s' % (k, getattr(self, k))
                         for k in job_resource_fields.keys())

    def __repr__(self):
        return '<Job (%s)>' % self.values()

    def unicode(self):
        return self.values()

    def update_links(self):
        """Update internal references to master/parent links"""
        self._followers = set()
        self._children = set()

        if self.master_id:
            get_job_or_404(self.master_id)._followers.add(self.job_id)

        if self.parent_id:
            get_job_or_404(self.parent_id)._children.add(self.job_id)

    def clean_links(self):
        """Clean job references in master/parent links"""
        for f in self.followers:
            f.master_id = None
        if self.master_id:
            get_job_or_404(self.master_id)._followers.remove(self.job_id)

        for c in self.children:
            c.parent_id = None
        if self.parent_id:
            get_job_or_404(self.parent_id)._children.remove(self.job_id)

    def update(self, status=None, progress=None):
        if status is not None:
            self.status = status
        if progress is not None and progress > self.progress:
            self.progress = progress

        self.calculate_progress()

    @property
    def followers(self):
        return [get_job_or_404(c) for c in self._followers]

    @property
    def children(self):
        return [get_job_or_404(c) for c in self._children]

    def calculate_progress(self):
        """Roll up progress from children and push progress to followers."""

        # when calculating progress for a parent job, assumptions are made
        # since not all jobs are necessarily created immediately; initial
        # progress when seeing a single child job complete gets tagged at
        # 33%, and overall progress gets capped at 90% to avoid the issue
        # of sitting at 100% for a long period.

        # XXXMFG make the params configurable

        children = self.children
        if children:
            if len(children) == 1 and children[0].status == 3:
                # one child so far, and it's complete
                self.progress = PARENT_MIN_PROGRESS
            else:
                num_done = sum(1 for c in children if c.status == 3)
                progress = int((num_done / float(len(children))) * 100)
                if progress > self.progress:
                    if progress > PARENT_MAX_PROGRESS:
                        progress = PARENT_MAX_PROGRESS
                    self.progress = progress

        for f in self.followers:
            # shadow jobs - push status and progress down
            f.status, f.progress = self.status, self.progress

        if self.master_id:
            get_job_or_404(self.master_id).calculate_progress()

        if self.parent_id:
            get_job_or_404(self.parent_id).calculate_progress()


job_resource_fields = OrderedDict([
    ('job_id', fields.Integer),
    ('status', fields.String),
    ('progress', fields.Integer),
    ('master_id', fields.Integer),
    ('parent_id', fields.Integer)
])
jobs_resource_fields = OrderedDict([
    ('items', fields.Nested(job_resource_fields, allow_null=True))
])


class JobAPI(Resource):
    @marshal_with(job_resource_fields)
    def get(self, job_id):
        job = get_job_or_404(job_id)
        print 'Received GET request for Job: %s' % job
        return job

    @marshal_with(job_resource_fields)
    def put(self, job_id):
        s = get_job_or_404(job_id)
        data = request.get_json()
        print 'Received PUT data for Job ID %d: %s' % (job_id, data)

        # id and master fields are read-only, remove if present
        data.pop('job_id', None)
        data.pop('master_id', None)
        s.update(**data)
        return s, 200

    def delete(self, job_id):
        j = get_job_or_404(job_id)
        j.clean_links()
        del JOBS[job_id]
        return '', 204


class JobRelationsAPI(Resource):
    def _get_followers(self, job_id):
        job = get_job_or_404(job_id)
        return {'followers': job.followers}

    def _get_children(self, job_id):
        job = get_job_or_404(job_id)
        return {'children': job.children}

    def _get_master(self, job_id):
        job = get_job_or_404(job_id)
        return {JOBS[job.master_id]}

    def _get_parent(self, job_id):
        job = get_job_or_404(job_id)
        return {JOBS[job.parent_id]}


class JobMasterAPI(JobRelationsAPI):
    @marshal_with(job_resource_fields)
    def get(self, job_id):
        print 'Received GET for master of Job ID: %s' % job_id
        return self._get_master(job_id)


class JobFollowersAPI(JobRelationsAPI):
    @marshal_with(job_resource_fields)
    def get(self, job_id):
        print 'Received GET for followers of Job ID: %s' % job_id
        return self._get_followers(job_id)


class JobChildrenAPI(JobRelationsAPI):
    @marshal_with(job_resource_fields)
    def get(self, job_id):
        print 'Received GET for children of Job ID: %s' % job_id
        return self._get_children(job_id)


class JobDoneAPI(JobRelationsAPI):
    @marshal_with(job_resource_fields)
    def post(self, job_id):
        print 'Received POST for completed Job ID: %s' % job_id
        return self._get_followers(job_id)


class JobListAPI(Resource):
    @marshal_with(jobs_resource_fields)
    def get(self):
        result = sorted(JOBS.values())
        return {'items': result}

    @marshal_with(job_resource_fields)
    def post(self):
        data = request.get_json()
        print 'Received POST data: %s' % data
        try:
            job_schema.validate(data)
        except ValidationError as e:
            abort(400, message=str(e))

        j = Job(**data)
        if j.job_id in JOBS:
            abort(409, message='Job with job_id %d already exists' % j.job_id)

        JOBS[j.job_id] = j
        return j, 201, {'Location': api.url_for(JobAPI, job_id=j.job_id)}


api.add_resource(JobListAPI, '/jobs/')
api.add_resource(JobAPI, '/jobs/<int:job_id>/')
api.add_resource(JobMasterAPI, '/jobs/<int:job_id>/master/')
api.add_resource(JobFollowersAPI, '/jobs/<int:job_id>/followers/')
api.add_resource(JobChildrenAPI, '/jobs/<int:job_id>/children/')
api.add_resource(JobDoneAPI, '/jobs/<int:job_id>/done/')


def load_existing_jobs():
    # Extract existing job model data and load
    cmd = 'cd %s && %s manage.py dumpdata jobs.job' % (project_path,
                                                       sys.executable)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         shell=True)
    stdout, stderr = p.communicate()

    if stderr:
        print 'Error while processing existing jobs:'
        print stderr
        sys.exit(1)

    jobs = json.loads(stdout)

    for j in jobs:
        job = Job(job_id=j['pk'],
                  status=j['fields']['status'],
                  progress=0,
                  master_id=j['fields']['master'])
        print 'Adding existing job %s' % job
        JOBS[j['pk']] = job

    # update references since jobs may have been added out of order
    for j in JOBS.itervalues():
        j.update_links()


if __name__ == '__main__':
    try:
        project_path = sys.argv[1]
    except IndexError:
        print 'Path to appfwk_project required'
        sys.exit(1)

    load_existing_jobs()

    app.run(host='127.0.0.1', debug=False)
