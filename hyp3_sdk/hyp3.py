import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urljoin

from requests.exceptions import HTTPError, RequestException

from hyp3_sdk.exceptions import HyP3Error, ValidationError
from hyp3_sdk.jobs import Batch, Job
from hyp3_sdk.util import get_authenticated_session

HYP3_PROD = 'https://hyp3-api.asf.alaska.edu'
HYP3_TEST = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API"""

    def __init__(self, api_url: str = HYP3_PROD, username: Optional = None, password: Optional = None):
        """
        Args:
            api_url: Address of the HyP3 API
            username: Username for authenticating to urs.earthdata.nasa.gov. Both username and password must be provided
            password: Password for authenticating to urs.earthdata.nasa.gov. Both username and password must be provided
        """
        self.url = api_url
        self.session = get_authenticated_session(username, password)

    def find_jobs(self, start: Optional[datetime] = None, end: Optional[datetime] = None,
                  status: Optional[str] = None, name: Optional[str] = None) -> Batch:
        """Gets a Batch of jobs from HyP3 matching the provided search criteria

        Args:
            start: only jobs submitted after given time
            end: only jobs submitted before given time
            status: only jobs matching this status (SUCCEEDED, FAILED, RUNNING, PENDING)
            name: only jobs with this name

        Returns:
            A Batch object containing the found jobs
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
        jobs = [Job.from_dict(job) for job in response['jobs']]
        return Batch(jobs)

    def _get_job_by_id(self, job_id):
        try:
            response = self.session.get(urljoin(self.url, f'/jobs/{job_id}'))
            response.raise_for_status()
        except RequestException:
            raise HyP3Error('Unable to get job by ID')
        return Job.from_dict(response.json())

    def watch(self, batch: Batch, timeout: int = 10800, interval: int = 60):
        """Watch jobs until they complete

        Args:
            batch: A Batch object containing the list of jobs to watch
            timeout: How long to wait until exiting in seconds
            interval: How often to check for updates in seconds

        Returns:
            A Batch object containing refreshed watched jobs
        """
        end_time = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end_time:
            batch = self.refresh(batch)
            if batch.complete():
                return batch
            time.sleep(interval)
        raise HyP3Error('Timeout occurred while waiting for jobs')

    def refresh(self, batch: Batch) -> Batch:
        """Refresh each jobs' information

        Args:
            batch: A Batch object containing the list of jobs to refresh

        Returns:
            A Batch object containing refreshed jobs
        """
        jobs = []
        for job in batch.jobs:
            jobs.append(self._get_job_by_id(job.job_id))
        return Batch(jobs)

    def _submit_raw_job(self, job_type: str, job_name: Optional[str], job_parameters: dict,
                        validate_only: bool = False) -> Job:
        job_dict = {
            'job_parameters': job_parameters,
            'job_type': job_type,
        }
        if job_name is not None:
            if len(job_name) > 20:
                raise ValidationError('Job name too long; must be less than 20 characters')
            job_dict['job_name'] = job_name

        payload = {'jobs': [job_dict], 'validate_only': validate_only}
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload)
        return Job.from_dict(response.json()['jobs'][0])

    def submit_autorift_job(self, granule1: str, granule2: str, job_name: Optional[str]) -> Job:
        """Submit an autoRIFT job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            job_name: A name for the job (must be <= 20 characters)

        Returns:
            A Batch object containing the autoRIFT job
        """
        job_parameters = {'granules': [granule1, granule2]}
        return self._submit_raw_job(
            job_type='AUTORIFT', job_name=job_name, job_parameters=job_parameters,
        )

    def submit_rtc_job(self, granule: str, job_name: Optional[str], **kwargs) -> Job:
        """Submit an RTC job

        Args:
            granule: The granule (scene) to use
            job_name: A name for the job (must be <= 20 characters)
            **kwargs: Extra job parameters specifying custom processing options

        Returns:
            A Batch object containing the RTC job
        """
        job_parameters = {'granules': [granule], **kwargs}
        return self._submit_raw_job(
            job_type='RTC_GAMMA', job_name=job_name, job_parameters=job_parameters,
        )

    def submit_insar_job(self, granule1: str, granule2: str, job_name: Optional[str], **kwargs) -> Job:
        """Submit an InSAR job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            job_name: A name for the job (must be <= 20 characters)
            **kwargs: Extra job parameters specifying custom processing options

        Returns:
            A Batch object containing the InSAR job
        """
        job_parameters = {'granules': [granule1, granule2], **kwargs}
        return self._submit_raw_job(
            job_type='INSAR_GAMMA', job_name=job_name, job_parameters=job_parameters,
        )

    def my_info(self) -> dict:
        """
        Returns:
            Your user information
        """
        try:
            response = self.session.get(urljoin(self.url, '/user'))
            response.raise_for_status()
        except HTTPError:
            raise HyP3Error('Unable to get user information from API')
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
            raise HyP3Error('Unable to get user information from API')
        return response.json()['quota']['remaining']
