# Copyright (c) 2015 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the MIT License
# accompanying the software ("License").  This software is distributed "AS IS"
# as set forth in the License.


import requests

URL = 'http://127.0.0.1:5000'
JURL = URL + '/jobs/'

commands = [
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 1}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 2, "master_id": 1}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 3, "master_id": 1}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 4, "master_id": 1}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 5, "master_id": 3}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 6, "master_id": 3}'),
    ('POST', None,
     '{"progress": 0, "status": 0, "job_id": 7, "master_id": 4}'),
    ('GET', 2, None),
    ('PUT', 2, '{"progress": 2, "status": 1}'),
    ('GET', 2, None),
    ('GET', 1, None),
    ('PUT', 2, '{"progress": 100, "status": 4}'),
    ('GET', 1, None),
    ('PUT', 7, '{"progress": 100, "status": 4}'),
    ('GET', 4, None),
    ('PUT', 4, '{"status": 4}'),
    ('GET', 4, None),
    ('GET', 1, None),
]

session = requests.session()
session.headers['Content-Type'] = 'application/json'
session.headers['Accept'] = 'application/json'

for method, id, d in commands:
    url = JURL
    if id:
        url = '%s%d/' % (JURL, id)

    r = session.request(method, url, data=d)
    print r.text
