from datetime import datetime, timedelta
import time
from typing import List, Optional, Union
from urllib.parse import urljoin

from requests import  HTTPError

from hyp3_sdk.jobs import BaseJob, RequestedJob
from hyp3_sdk.util import get_authenticated_session
from hyp3_sdk.exceptions import ValidationError, Hyp3SdkError

HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API"""

    def __init__(self, api_url: str = HYP3_PROD, username : Optional = None, password: Optional = None):
        """
        Args:
            api_url: Address of the HyP3 API
            username: Username to use for authentication to urs.earthdata.nasa.gov, if provided password must be provided
            password: Password to use for authentication to urs.earthdata.nasa.gov, if provided username must be provided
        """
        self.url = api_url
        self.session = get_authenticated_session(username, password)

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

    def _get_job_by_id(self, job_id):
        try:
            response = self.session.get(urljoin(self.url, f'/jobs/{job_id}'))
            response.raise_for_status()
        except:
            raise Hyp3SdkError('Unable to get job by ID')
        return RequestedJob.from_dict(response.json())

    def get_jobs(self, jobs: List[RequestedJob]):
        """
        Args:
            jobs: list of RequestedJobs to get from api

        Returns: A new list of corresponding jobs from the api
        """
        job_ids = [job.id for job in jobs]
        new_jobs = [self._get_job_by_id(job_id) for job_id in job_ids]
        return new_jobs

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
        jobs = [RequestedJob.from_dict(job) for job in response['jobs']]
        return jobs

    def submit_jobs(self, jobs: List[BaseJob], validate_only: bool = False,
                    force_resubmit: bool = False) -> List[RequestedJob]:
        """Submit jobs to the API
        Args:
            jobs: A list of Job instances to submit to the API
            validate_only: Instead of submitting, just validate `jobs`
            force_resubmit:

        Returns:
            The full dictionary representation of the HyP3 API response
        """
        payload = {
            'jobs': [job.to_dict() for job in jobs],
            'validate_only': validate_only,
        }
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload).json()
        jobs = [RequestedJob.from_dict(job) for job in response['jobs']]
        return jobs

    @staticmethod
    def jobs_are_complete(jobs: List[RequestedJob]) -> bool:
        """
        Args:
            jobs: List of jobs to check

        Returns: True if all jobs are complete, otherwise returns False
        """
        for job in jobs:
            if not job.is_complete():
                return False
        return True

    def wait_for_jobs(self, jobs: List['RequestedJob'], timeout: int = 10800, interval: int = 60):
        """
        Args:
            jobs: List of jobs to wait for
            timeout: How long to wait until exiting in seconds
            interval: How often to check for updates in seconds

        Returns: list of completed jobs once complete, or raises in case of timeout
        """
        end_time = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end_time:
            updated_jobs = self.get_jobs(jobs)
            if self.jobs_are_complete(updated_jobs):
                return updated_jobs
            time.sleep(interval)
        raise Hyp3SdkError('Timeout occurred while waiting for jobs')

    def my_info(self) -> dict:
        """
        Returns:
            Your user information
        """
        try:
            response = self.session.get(urljoin(self.url, '/user'))
            response.raise_for_status()
        except HTTPError:
            raise Hyp3SdkError('Unable to get user information from API')
        return response.json()

    def check_quota(self) -> int:
        """
        Returns:
            The number of jobs left in your quota
        """
        try:
            response = self.session.get(urljoin(self.url, '/user'))
            response.raise_for_status()
        except HTTPError:
            raise Hyp3SdkError('Unable to get user information from API')
        return response.json()['quota']['remaining']
