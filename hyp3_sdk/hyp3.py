from datetime import datetime
from typing import List
from urllib.parse import urljoin

import requests

from hyp3_sdk.jobs import Job
from hyp3_sdk.util import get_authenticated_session

HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the hyp3-api"""

    def __init__(self, api_url: str = HYP3_PROD, authenticated_session: requests.session = None):
        self.url = api_url
        self.session = authenticated_session
        if self.session is None:
            self.session = get_authenticated_session()

    def get_jobs(self, start: datetime = None, end: datetime = None, status: str = None) -> dict:
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
        return self.session.get(urljoin(self.url, '/jobs'), params=params).json()

    def submit_jobs(self, jobs: List[Job], validate_only: bool = False) -> dict:
        payload = {
            'jobs': [job.to_dict() for job in jobs],
            'validate_only': validate_only,
        }
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload)
        return response.json()

    def get_quota(self):
        return self.session.get(urljoin(self.url, '/user')).json()['quota']
