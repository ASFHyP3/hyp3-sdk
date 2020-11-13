from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dateutil.parser import parse as parse_date\

from hyp3_sdk.exceptions import Hyp3SdkError, ValidationError
from hyp3_sdk.util import download_file

class BaseJob:
    """Jobs to be submitted to the API"""
    def __init__(self, job_type: str, job_name: Optional[str] = None, job_parameters: Optional[dict] = None):
        """Create a new Job object

        Args:
            job_type: The job type
            job_name: A name for the job (must be <= 20 characters)
            job_parameters: Extra job parameters specifying custom processing options
        """
        if len(job_name) > 20:
            raise ValidationError('Job name too long, must be less then 20 chars')
        self.job_name = job_name
        self.job_type = job_type
        self.job_parameters = job_parameters if job_parameters is not None else {}

    def to_dict(self) -> dict:
        """
        Returns:
            A dictionary representation of the Job object
        """
        return {
            'job_parameters': {
                **self.job_parameters
            },
            'job_type': self.job_type,
            'name': self.job_name,
        }

    @staticmethod
    def from_dict(input_dict: dict):
        return BaseJob(input_dict['job_type'], input_dict['job_name'], input_dict['job_parameters'])


class RequestedJob(BaseJob):
    def __init__(
            self,
            job_type: str,
            job_id: str,
            request_time: datetime,
            status_code: str,
            user_id: str,
            job_name: Optional[str],
            job_parameters: dict,
            files: Optional[List] = None,
            browse_images: Optional[List] = None,
            thumbnail_images: Optional[List] = None,
            expiration_time: Optional[datetime] = None
            ):
        self.id = job_id
        self.job_type = job_type
        self.request_time = request_time
        self.status_code = status_code
        self.user_id = user_id
        self.job_name = job_name
        self.job_parameters = job_parameters
        self.files = files
        self.browse_images = browse_images
        self.thumbnail_images = thumbnail_images
        self.expiration_time = expiration_time

    @staticmethod
    def from_dict(input_dict: dict):
        expiration_time = parse_date(input_dict['expiration_time']) if input_dict.get('expiration_time') else None
        return RequestedJob(
            input_dict['job_type'],
            input_dict['job_id'],
            input_dict['request_time'],
            input_dict['status_code'],
            input_dict['user_id'],
            input_dict['job_parameters'],
            files=input_dict.get('files'),
            browse_images=input_dict.get('browse_images'),
            thumbnail_images=input_dict.get('thumbnail_images'),
            expiration_time=expiration_time
        )

    def is_complete(self) -> bool:
        return self.status_code in ('FAILED', 'SUCCEEDED')

    def is_expired(self) -> bool:
        return datetime.utcnow() >= self.expiration_time

    def download_files(self, location: Path) -> List[Path]:
        """

        Args:
            location: Directory location to put files into

        Returns: list of Path objects to downloaded files

        """
        if not self.is_complete():
            raise Hyp3SdkError('Incomplete jobs cannot be downloaded')
        downloaded_files = []
        for file in self.files:
            download_url = file['url']
            filename = location / file['filename']
            try:
                downloaded_files.append(download_file(download_url, filename))
            except Exception:
                raise Hyp3SdkError('unable to download file')
        return downloaded_files


def autorift(job_name: str, granule1: str, granule2: str, **kwargs) -> BaseJob:
    """Make an autoRIFT Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule1: The first granule (scene) to use
        granule2: The second granule (scene) to use
        **kwargs: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return BaseJob(job_type='AUTORIFT', job_name=job_name, job_parameters=kwargs)

@staticmethod
def rtc(job_name: str, granule: str, **kwargs) -> BaseJob:
    """Make an RTC Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule: The granule (scene) to process
        **kwargs: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return BaseJob(job_type='RTC_GAMMA', job_name=job_name, job_parameters=kwargs)

@staticmethod
def insar(job_name: str, granule1: str, granule2: str, kwargs) -> BaseJob:
    """Make an InSAR Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule1: The first granule (scene) to use
        granule2: The second granule (scene) to use
        **kwargs: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return BaseJob(job_type='INSAR_GAMMA', job_name=job_name, job_parameters=kwargs)
