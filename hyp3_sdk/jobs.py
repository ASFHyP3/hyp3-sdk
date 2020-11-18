import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union

from dateutil import tz
from dateutil.parser import parse as parse_date

from hyp3_sdk.exceptions import HyP3Error
from hyp3_sdk.util import download_file


# TODO: actually looks like a good candidate for a dataclass (python 3.7+)
#       https://docs.python.org/3/library/dataclasses.html
class Job:
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
        self.browse_images = browse_images
        self.thumbnail_images = thumbnail_images
        self.expiration_time = expiration_time

    def __repr__(self):
        return str(self.to_dict())

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
            browse_images=input_dict.get('browse_images'),
            thumbnail_images=input_dict.get('thumbnail_images'),
            expiration_time=expiration_time
        )

    def to_dict(self, for_resubmit: bool = False):
        job_dict = {
            'job_type': self.job_type,
        }

        for key in ['name', 'job_parameters']:
            value = self.__getattribute__(key)
            if value is not None:
                job_dict[key] = value

        if not for_resubmit:
            for key in ['files', 'browse_images', 'thumbnail_images', 'job_id', 'status_code', 'user_id',
                        'expiration_time', 'request_time']:
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
            raise HyP3Error('Only SUCCEEDED jobs have an expiration time')

    # TODO: handle expired products
    def download_files(self, location: Path) -> List[Path]:
        """
        Args:
            location: Directory location to put files into

        Returns: list of Path objects to downloaded files
        """
        if not self.complete():
            raise HyP3Error('Incomplete jobs cannot be downloaded')
        downloaded_files = []
        for file in self.files:
            download_url = file['url']
            filename = location / file['filename']
            try:
                downloaded_files.append(download_file(download_url, filename))
            except Exception:
                raise HyP3Error('unable to download file')
        return downloaded_files


class Batch:
    def __init__(self, jobs: List[Job]):
        if len(jobs) == 0:
            warnings.warn('Jobs list is empty; creating an empty Batch', UserWarning)

        self.jobs = jobs

    def __len__(self):
        return len(self.jobs)

    def __add__(self, other: Union[Job, 'Batch']):
        if isinstance(other, Batch):
            return Batch(self.jobs + other.jobs)
        elif isinstance(other, Job):
            return Batch(self.jobs + [other])
        else:
            raise TypeError(f"unsupported operand type(s) for +: '{type(self)}' and '{type(other)}'")

    def __repr__(self):
        return str([job.to_dict() for job in self.jobs])

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

    # TODO: skip expired products
    def download_files(self, location: Path) -> List[Path]:
        """
        Args:
            location: Directory location to put files into

        Returns: list of Path objects to downloaded files
        """
        if not self.complete():
            raise HyP3Error('Incomplete jobs cannot be downloaded')
        downloaded_files = []
        for job in self.jobs:
            downloaded_files.extend(job.download_files(location))
        return downloaded_files

    def any_expired(self) -> bool:
        """Check succeeded jobs for expiration"""
        for job in self.jobs:
            try:
                if job.expired():
                    return True
            except HyP3Error:
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
