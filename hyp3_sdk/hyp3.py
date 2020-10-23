from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import requests

from hyp3_sdk.jobs import Job
from hyp3_sdk.util import get_authenticated_session

HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API"""
    def __init__(self, api_url: str = HYP3_PROD, authenticated_session: Optional[requests.Session] = None):
        """

        Args:
            api_url: Address of the HyP3 API
            authenticated_session: An authenticated Earthdata Login session to use
        """
        self.url = api_url
        self.session = authenticated_session
        if self.session is None:
            self.session = get_authenticated_session()

    def get_jobs(self, start: Optional[datetime] = None, end: Optional[datetime] = None,
                 status: Optional[str] = None, name: Optional[str] = None) -> dict:
        """Get your jobs

        Args:
            start: only jobs submitted after given time
            end: only jobs submitted before given time
            status: only jobs matching this status (SUCCEEDED, FAILED, RUNNING, PENDING)
            name: only jobs with this name

        Returns:
            The full dictionary representation of the HyP3 API response
        """
        params = {}
        if name is not None:
            params['name'] = name
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
        """Submit jobs to the API

        Args:
            jobs: A list of Job instances to submit to the API
            validate_only: Instead of submitting, just validate `jobs`

        Returns:
            The full dictionary representation of the HyP3 API response
        """
        payload = {
            'jobs': [job.to_dict() for job in jobs],
            'validate_only': validate_only,
        }
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload)
        return response.json()

    def get_quota(self) -> dict:
        """
        Returns:
            Your current quota
        """
        return self.session.get(urljoin(self.url, '/user')).json()['quota']
