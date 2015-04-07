import requests

URL = 'http://127.0.0.1:5000'
JURL = URL + '/jobs/'

commands = [
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 1}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 2, "parent_id": 1}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 3, "parent_id": 1}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 4, "parent_id": 1}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 5, "parent_id": 3}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 6, "parent_id": 3}'),
    ('POST', None, '{"progress": 0, "state": "NEW", "id": 7, "parent_id": 4}'),
    ('GET', 2, None),
    ('PUT', 2, '{"progress": 2, "state": "RUNNING"}'),
    ('GET', 2, None),
    ('GET', 1, None),
    ('PUT', 2, '{"progress": 100, "state": "COMPLETE"}'),
    ('GET', 1, None),
    ('PUT', 7, '{"progress": 100, "state": "COMPLETE"}'),
    ('GET', 4, None),
    ('PUT', 4, '{"state": "COMPLETE"}'),
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
