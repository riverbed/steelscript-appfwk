# Copyright (c) 2014 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.

import os
import sys
import json
import logging
from collections import OrderedDict

from flask import Flask, request
from flask_restful import Resource, Api, abort, fields, marshal_with


import reschema

#logging.basicConfig(filename='progressd.log',level=logging.DEBUG)
logger = logging.getLogger(__name__)


app = Flask(__name__)
api = Api(app)

# API Service Definitions
service = reschema.ServiceDef()
service.load('progressd.yaml')
job_schema = service.find_resource('job')
jobs_schema = service.find_resource('jobs')

# Valid Job status
VALID_STATUS = (0, 1, 3, 4)

# Map of Job IDs to Job objects
JOBS = {}


def get_job_or_404(job_id):
    if job_id not in JOBS:
        abort(404, message="Job {} not found".format(job_id))
    return JOBS[job_id]


class Job(object):
    """Basic datastructure for Job status"""

    resource_fields = OrderedDict(
        job_id=fields.Integer,
        status=fields.String,
        progress=fields.Integer,
        parent_id=fields.Integer
    )

    def __init__(self, job_id, status, progress, parent_id=None):
        self.job_id = job_id
        self.status = status
        self.progress = progress
        self.parent_id = parent_id

        # calculated field
        self._children = set()

        if self.parent_id:
            get_job_or_404(self.parent_id)._children.add(self.job_id)

    def __cmp__(self, other):
        return cmp(self.job_id, other.job_id)

    def values(self):
        return ', '.join('%s: %s' % (k, getattr(self, k))
                         for k in self.resource_fields.keys())

    def __repr__(self):
        return '<Job (%s)>' % self.values()

    def unicode(self):
        return self.values()

    def update(self, status=None, progress=None):
        if status is not None and status in VALID_STATUS:
            self.status = status
        if progress is not None and progress > self.progress:
            self.progress = progress

        self.calculate_progress()

    @property
    def children(self):
        return [get_job_or_404(c) for c in self._children]

    def calculate_progress(self):
        for child in self.children:
            # shadow jobs - push status and progress down
            child.status, child.progress = self.status, self.progress

        if self.parent_id:
            get_job_or_404(self.parent_id).calculate_progress()


class JobAPI(Resource):
    @marshal_with(Job.resource_fields)
    def get(self, job_id):
        print 'Received GET request for Job ID: %s' % job_id
        return get_job_or_404(job_id)

    @marshal_with(Job.resource_fields)
    def put(self, job_id):
        s = get_job_or_404(job_id)
        data = request.get_json()
        print 'Received PUT data for Job ID %d: %s' % (job_id, data)

        # id and parent fields are read-only, remove if present
        data.pop('job_id', None)
        data.pop('parent_id', None)
        s.update(**data)
        return s, 201

    def delete(self, job_id):
        get_job_or_404(job_id)
        del JOBS[job_id]
        return '', 204


class JobListAPI(Resource):
    @marshal_with(Job.resource_fields)
    def get(self):
        result = sorted(JOBS.values())
        return result

    @marshal_with(Job.resource_fields)
    def post(self):
        data = request.get_json()
        print 'Received POST data: %s' % data
        job_schema.validate(data)

        j = Job(**data)
        JOBS[j.job_id] = j
        return JOBS[j.job_id], 201


api.add_resource(JobListAPI, '/jobs/')
api.add_resource(JobAPI, '/jobs/<int:job_id>/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
