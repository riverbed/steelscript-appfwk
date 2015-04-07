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
from flask_restful import Resource, Api, fields, marshal_with


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

# Valid Job states
VALID_STATES = ('NEW', 'RUNNING', 'COMPLETE', 'ERROR')

# Map of Job IDs to Job objects
JOBS = {}


class Job(object):
    """Basic datastructure for Job state"""

    resource_fields = OrderedDict(
        id=fields.Integer,
        state=fields.String,
        progress=fields.Integer,
        parent_id=fields.Integer
    )

    def __init__(self, id, state, progress, parent_id=None):
        self.id = id
        self.state = state
        self.progress = progress
        self.parent_id = parent_id

        # calculated field
        self._children = set()

        if self.parent_id:
            JOBS[self.parent_id]._children.add(self.id)

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    def values(self):
        return ', '.join('%s: %s' % (k, getattr(self, k))
                         for k in self.resource_fields.keys())

    def __repr__(self):
        return '<Job (%s)>' % self.values()

    def unicode(self):
        return self.values()

    def update(self, state=None, progress=None):
        if state is not None and state in VALID_STATES:
            self.state = state
        if progress is not None and progress > self.progress:
            self.progress = progress

        self.calculate_progress()

    @property
    def children(self):
        return [JOBS[c] for c in self._children]

    def calculate_progress(self):
        children = self.children

        if children:
            if len(children) == 1:
                # convert to list since can't iterate list
                child = children[0]
                self.progress = JOBS[child.id].progress
            else:
                done_count = sum(c.state == 'COMPLETE' for c in children)
                self.progress = (float(done_count) / len(children)) * 100

        if self.parent_id:
            JOBS[self.parent_id].calculate_progress()


class JobAPI(Resource):
    @marshal_with(Job.resource_fields)
    def get(self, id):
        print 'Received GET request for Job ID: %s' % id
        return JOBS[id]

    @marshal_with(Job.resource_fields)
    def put(self, id):
        s = JOBS[id]
        data = request.get_json()
        print 'Received PUT data for Job ID %d: %s' % (id, data)

        # id and parent fields are read-only, remove if present
        data.pop('id', None)
        data.pop('parent_id', None)
        s.update(**data)
        return s, 201

    def delete(self, id):
        del JOBS[id]
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
        print 'Job object created: %s' % j
        JOBS[j.id] = j
        return JOBS[j.id], 201


api.add_resource(JobListAPI, '/jobs/')
api.add_resource(JobAPI, '/jobs/<int:id>/')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
