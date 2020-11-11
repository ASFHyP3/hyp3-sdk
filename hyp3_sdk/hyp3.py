from datetime import datetime
from typing import List, Optional, Union
from urllib.parse import urljoin

from hyp3_sdk.jobs import BaseJob, RequestedJob
from hyp3_sdk.util import get_authenticated_session

HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API"""

    def __init__(self, api_url: str = HYP3_PROD, username : Optional = None, password: Optional = None):
        """

        Args:
            api_url: Address of the HyP3 API
            authenticated_session: An authenticated Earthdata Login session to use
        """
        self.url = api_url
        get_authenticated_session(username, password)

    @staticmethod
    def supported_job_types() -> tuple:
        """
        Returns:
            The job types that are able to be processed by HyP3
        """
        return (
            'RTC_GAMMA',
            'INSAR_GAMMA',
            'AUTORIFT',
        )

    def get_jobs(self, jobs: List[Union[BaseJob, RequestedJob]]):
        pass

    def search_jobs(self, start: Optional[datetime] = None, end: Optional[datetime] = None,
                 status: Optional[str] = None, name: Optional[str] = None) -> List[RequestedJob]:
        """Gets jobs from hyp3 matching the procided search criteria

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

        response = self.session.get(urljoin(self.url, '/jobs'), params=params).json()
        jobs = [RequestedJobs.from_dict(job) for job in response['jobs']]
        return jobs

    def submit_jobs(self, jobs: List[Union[BaseJob, RequestedJob]], validate_only: bool = False,
                    force_resubmit: bool = False) -> List[RequestedJob]:
        """Submit jobs to the API

        Args:
            jobs: A list of Job instances to submit to the API
            validate_only: Instead of submitting, just validate `jobs`
            force_resubmit:

        Returns:
            The full dictionary representation of the HyP3 API response
        """
        for job in jobs:
            if isinstance(RequestedJob): # single disbatch submission?
                if not job.is_expired() and not force_resubmit:
                    raise ...

        payload = {
            'jobs': [job.to_dict() for job in jobs],
            'validate_only': validate_only,
        }
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload).json()
        jobs = [RequestedJobs.from_dict(job) for job in response['jobs']]
        return jobs

    def jobs_are_complete(self, jobs: List[RequestedJob],
                          wait: bool = False, timeout: int = 10800, check_every: int = 60) -> bool:



    def my_info(self) -> dict:
        """
        Returns:
            Your user information
        """
        return self.session.get(urljoin(self.url, '/user')).json()

    def check_quota(self) -> int:
        """
        Returns:
            The number of jobs left in your quota
        """
        return self.session.get(urljoin(self.url, '/user')).json()['quota']["remaining"]
