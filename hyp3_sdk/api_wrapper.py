from datetime import datetime, timezone
from urllib.parse import urljoin

import requests

from hyp3_sdk.util import get_auth_token


HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class Hyp3():
    """A python wrapper around the hyp3-api"""

    def __init__(self, api_url=HYP3_PROD, token=None):
        self.url = api_url
        self.token = token
        if self.token == None:
            self.token = get_auth_token()

    def get_jobs(self, start: datetime = None, end: datetime = None, status: str = None):
        cookie = {'asf-urs': self.token}
        params = {}
        if start is not None:
            params['start'] = start.isoformat(timespec='seconds')
            if start.tzinfo is None:
                params['start'] += 'Z'
        if end is not None:
            params['end'] = end.isoformat(timespec='seconds')
            if end.tzinfo is None:
                params['end'] += 'Z'
        if status is not None:
            params['status_code'] = status
        return requests.get(urljoin(self.url, '/jobs'), params=params, cookies=cookie).json()

    def submit_jobs(self, granules, description=' ', job_type='RTC_GAMMA'):
        payload = {
            'jobs': [
                {
                    'job_type': job_type,
                    'description': description,
                    'job_parameters': {
                        'granule': granule
                    }
                } for granule in granules
            ]
        }
        cookie = {'asf-urs': self.token}
        return requests.post(urljoin(self.url, '/jobs'), json=payload, cookies=cookie).json()
