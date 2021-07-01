from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from dateutil import tz
from dateutil.parser import parse as parse_date
from requests import HTTPError

from hyp3_sdk.exceptions import HyP3SDKError
from hyp3_sdk.util import download_file, get_tqdm_progress_bar


# TODO: actually looks like a good candidate for a dataclass (python 3.7+)
#       https://docs.python.org/3/library/dataclasses.html
class Job:
    _attributes_for_resubmit = {'name', 'job_parameters', 'job_type'}

    def __init__(
            self,
            job_type: str,
            job_id: str,
            request_time: datetime,
            status_code: str,
            user_id: str,
            name: Optional[str] = None,
            job_parameters: Optional[dict] = None,
            files: Optional[List] = None,
            logs: Optional[List] = None,
            browse_images: Optional[List] = None,
            thumbnail_images: Optional[List] = None,
            expiration_time: Optional[datetime] = None
    ):
        self.job_id = job_id
        self.job_type = job_type
        self.request_time = request_time
        self.status_code = status_code
        self.user_id = user_id
        self.name = name
        self.job_parameters = job_parameters
        self.files = files
        self.logs = logs
        self.browse_images = browse_images
        self.thumbnail_images = thumbnail_images
        self.expiration_time = expiration_time

    def __repr__(self):
        return f'Job.from_dict({self.to_dict()})'

    def __str__(self):
        return f'HyP3 {self.job_type} job {self.job_id}'

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    @staticmethod
    def from_dict(input_dict: dict):
        expiration_time = parse_date(input_dict['expiration_time']) if input_dict.get('expiration_time') else None
        return Job(
            job_type=input_dict['job_type'],
            job_id=input_dict['job_id'],
            request_time=parse_date(input_dict['request_time']),
            status_code=input_dict['status_code'],
            user_id=input_dict['user_id'],
            name=input_dict.get('name'),
            job_parameters=input_dict.get('job_parameters'),
            files=input_dict.get('files'),
            logs=input_dict.get('logs'),
            browse_images=input_dict.get('browse_images'),
            thumbnail_images=input_dict.get('thumbnail_images'),
            expiration_time=expiration_time
        )

    def to_dict(self, for_resubmit: bool = False):
        job_dict = {}
        if for_resubmit:
            keys_to_process = Job._attributes_for_resubmit
        else:
            keys_to_process = vars(self).keys()

        for key in keys_to_process:
            value = self.__getattribute__(key)
            if value is not None:
                if isinstance(value, datetime):
                    job_dict[key] = value.isoformat(timespec='seconds')
                else:
                    job_dict[key] = value

        return job_dict

    def succeeded(self) -> bool:
        return self.status_code == 'SUCCEEDED'

    def failed(self) -> bool:
        return self.status_code == 'FAILED'

    def complete(self) -> bool:
        return self.succeeded() or self.failed()

    def running(self) -> bool:
        return not self.complete()

    def expired(self) -> bool:
        try:
            return datetime.now(tz.UTC) >= self.expiration_time
        except TypeError:
            raise HyP3SDKError('Only SUCCEEDED jobs have an expiration time')

    def download_files(self, location: Union[Path, str] = '.', create: bool = True) -> List[Path]:
        """
        Args:
            location: Directory location to put files into
            create: Create `location` if it does not point to an existing directory

        Returns: list of Path objects to downloaded files
        """
        location = Path(location)

        if not self.succeeded():
            raise HyP3SDKError(f'Only succeeded jobs can be downloaded; job is {self.status_code}.')
        if self.expired():
            raise HyP3SDKError(f'Expired jobs cannot be downloaded; '
                               f'job expired {self.expiration_time.isoformat(timespec="seconds")}.')

        if create:
            location.mkdir(parents=True, exist_ok=True)
        elif not location.is_dir():
            raise NotADirectoryError(str(location))

        downloaded_files = []
        for file in self.files:
            download_url = file['url']
            filename = location / file['filename']
            try:
                downloaded_files.append(download_file(download_url, filename, chunk_size=10485760))
            except HTTPError:
                raise HyP3SDKError(f'Unable to download file: {download_url}')
        return downloaded_files


class Batch:
    def __init__(self, jobs: Optional[List[Job]] = None):
        if jobs is None:
            jobs = []
        self.jobs = jobs

    def __add__(self, other: Union[Job, 'Batch']):
        if isinstance(other, Batch):
            return Batch(self.jobs + other.jobs)
        elif isinstance(other, Job):
            return Batch(self.jobs + [other])
        else:
            raise TypeError(f"unsupported operand type(s) for +: '{type(self)}' and '{type(other)}'")

    def __iadd__(self, other: Union[Job, 'Batch']):
        if isinstance(other, Batch):
            self.jobs += other.jobs
        elif isinstance(other, Job):
            self.jobs += [other]
        else:
            raise TypeError(f"unsupported operand type(s) for +=: '{type(self)}' and '{type(other)}'")
        return self

    def __iter__(self):
        return iter(self.jobs)

    def __len__(self):
        return len(self.jobs)

    def __contains__(self, job: Job):
        return job in self.jobs

    def __delitem__(self, job: Job):
        self.jobs.pop(job)
        return self

    def __getitem__(self, index: int):
        return self.jobs[index]

    def __setitem__(self, index: int, job: Job):
        self.jobs[index] = job
        return self

    def __reverse__(self):
        for job in self.jobs[::-1]:
            yield job

    def __repr__(self):
        reprs = ", ".join([job.__repr__() for job in self.jobs])
        return f'Batch([{reprs}])'

    def __str__(self):
        count = self._count_statuses()
        return f'{len(self)} HyP3 Jobs: ' \
               f'{count["SUCCEEDED"]} succeeded, ' \
               f'{count["FAILED"]} failed, ' \
               f'{count["RUNNING"]} running, ' \
               f'{count["PENDING"]} pending.'

    def _count_statuses(self):
        return Counter([job.status_code for job in self.jobs])

    def complete(self) -> bool:
        """
        Returns: True if all jobs are complete, otherwise returns False
        """
        for job in self.jobs:
            if not job.complete():
                return False
        return True

    def succeeded(self) -> bool:
        """
        Returns: True if all jobs have succeeded, otherwise returns False
        """
        for job in self.jobs:
            if not job.succeeded():
                return False
        return True

    def download_files(self, location: Union[Path, str] = '.', create: bool = True) -> List[Path]:
        """
        Args:
            location: Directory location to put files into
            create: Create `location` if it does not point to an existing directory

        Returns: list of Path objects to downloaded files
        """
        downloaded_files = []
        tqdm = get_tqdm_progress_bar()
        for job in tqdm(self.jobs):
            try:
                downloaded_files.extend(job.download_files(location, create))
            except HyP3SDKError as e:
                print(f'Warning: {e}. Skipping download for {job}.')
        return downloaded_files

    def any_expired(self) -> bool:
        """Check succeeded jobs for expiration"""
        for job in self.jobs:
            try:
                if job.expired():
                    return True
            except HyP3SDKError:
                continue
        return False

    def filter_jobs(
            self, succeeded: bool = True, running: bool = True, failed: bool = False, include_expired: bool = True,
    ) -> 'Batch':
        """Filter jobs by status. By default, only succeeded and still running jobs will be in the returned batch.

        Args:
            succeeded: Include all succeeded jobs
            running: Include all running jobs
            failed: Include all failed jobs
            include_expired: Include expired jobs in the result


        Returns:
             batch: A batch object containing jobs matching all the selected statuses
        """
        filtered_jobs = []

        for job in self.jobs:
            if job.succeeded() and succeeded:
                if include_expired or not job.expired():
                    filtered_jobs.append(job)

            elif job.running() and running:
                filtered_jobs.append(job)

            elif job.failed() and failed:
                filtered_jobs.append(job)

        return Batch(filtered_jobs)
