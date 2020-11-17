import time
from datetime import datetime, timedelta
from functools import singledispatchmethod
from typing import Optional, Union
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
            username: Username for authenticating to urs.earthdata.nasa.gov.
                Both username and password must be provided if either is provided.
            password: Password for authenticating to urs.earthdata.nasa.gov.
               Both username and password must be provided if either is provided.
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

        response = self.session.get(urljoin(self.url, '/jobs'), params=params)
        try:
            response.raise_for_status()
        except HTTPError:
            raise HyP3Error(f'Error while trying to query {response.url}')
        jobs = [Job.from_dict(job) for job in response.json()['jobs']]
        return Batch(jobs)

    def _get_job_by_id(self, job_id):
        try:
            response = self.session.get(urljoin(self.url, f'/jobs/{job_id}'))
            response.raise_for_status()
        except RequestException:
            raise HyP3Error('Unable to get job by ID')
        return Job.from_dict(response.json())

    # TODO: Some sort of visual indication this is still going
    def watch(self, job_or_batch: Union[Batch, Job], timeout: int = 10800, interval: Union[int, float] = 60):
        """Watch jobs until they complete

        Args:
            job_or_batch: A Batch or Job object of jobs to watch
            timeout: How long to wait until exiting in seconds
            interval: How often to check for updates in seconds

        Returns:
            A Batch or Job object with refreshed watched jobs
        """
        end_time = datetime.now() + timedelta(seconds=timeout)
        while datetime.now() < end_time:
            job_or_batch = self.refresh(job_or_batch)
            if job_or_batch.complete():
                return job_or_batch
            time.sleep(interval)
        raise HyP3Error('Timeout occurred while waiting for jobs')

    @singledispatchmethod
    def refresh(self, job_or_batch: Union[Batch, Job]) -> Union[Batch, Job]:
        """Refresh each jobs' information

        Args:
            job_or_batch: A Batch of Job object to refresh

        Returns:
            obj: A Batch or Job object with refreshed information
        """
        raise NotImplementedError(f'Cannot refresh {type(job_or_batch)} type object')

    @refresh.register
    def _refresh_batch(self, batch: Batch):
        jobs = []
        for job in batch.jobs:
            jobs.append(self.refresh(job))
        return Batch(jobs)

    @refresh.register
    def _refresh_job(self, job: Job):
        return self._get_job_by_id(job.job_id)

    def submit_job_dict(self, job_dict: dict, name: Optional[str] = None, validate_only: bool = False) -> Job:
        if name is not None:
            if len(name) > 20:
                raise ValidationError('Job name too long; must be less than 20 characters')
            job_dict['name'] = name

        payload = {'jobs': [job_dict], 'validate_only': validate_only}
        response = self.session.post(urljoin(self.url, '/jobs'), json=payload)
        try:
            response.raise_for_status()
        except HTTPError:
            raise HyP3Error('Error while submitting job to HyP3')
        return Job.from_dict(response.json()['jobs'][0])

    def submit_autorift_job(self, granule1: str, granule2: str, name: Optional[str] = None) -> Job:
        """Submit an autoRIFT job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job (must be <= 20 characters)

        Returns:
            A Batch object containing the autoRIFT job
        """
        job_dict = {
            'job_parameters': {'granules': [granule1, granule2]},
            'job_type': 'AUTORIFT',
        }
        return self.submit_job_dict(job_dict=job_dict, name=name)

    def submit_rtc_job(self, granule: str, name: Optional[str] = None, **kwargs) -> Job:
        """Submit an RTC job

        Args:
            granule: The granule (scene) to use
            name: A name for the job (must be <= 20 characters)
            **kwargs: Extra job parameters specifying custom processing options

        Returns:
            A Batch object containing the RTC job
        """
        job_dict = {
            'job_parameters': {'granules': [granule], **kwargs},
            'job_type': 'RTC_GAMMA',
        }
        return self.submit_job_dict(job_dict=job_dict, name=name)

    def submit_insar_job(self, granule1: str, granule2: str, name: Optional[str] = None, **kwargs) -> Job:
        """Submit an InSAR job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job (must be <= 20 characters)
            **kwargs: Extra job parameters specifying custom processing options

        Returns:
            A Batch object containing the InSAR job
        """
        job_dict = {
            'job_parameters': {'granules': [granule1, granule2], **kwargs},
            'job_type': 'INSAR_GAMMA',
        }
        return self.submit_job_dict(job_dict=job_dict, name=name)

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
        info = self.my_info()
        return info['quota']['remaining']
