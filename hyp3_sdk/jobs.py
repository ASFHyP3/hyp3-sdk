from hyp3_sdk.exceptions import ValidationError


class BaseJob:
    """Jobs to be submitted to the API"""
    def __init__(self, job_type: str, job_name: Optional[str] = None, job_parameters: dict = {}):
        """Create a new Job object

        Args:
            job_type: The job type
            job_name: A name for the job (must be <= 20 characters)
            job_parameters: Extra job parameters specifying custom processing options
        """
        if job_type not in JOB_TYPES:  # FIXME: warning instead??
            raise ValidationError(f'Invalid job type: {job_type}, must be one of {JOB_TYPES}')
        if len(job_name) > 20:
            raise ValidationError('Job name too long, must be less then 20 chars')
        self.job_name = job_name
        self.job_type = job_type
        self.job_parameters = job_parameters

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
    def from_dict( ):

    def submit(self):

class JobTemplate():
    @staticmethod
    def autorift(job_name: str, granule1: str, granule2: str, kwargs) -> BaseJob:
        """Make an autoRIFT Job object

        Args:
            job_name: A name for the job (must be <= 20 characters)
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use

        Returns:
            A Job object
        """
        # TODO: warn about unsupported kwargs
        return BaseJob(job_type='AUTORIFT', job_name=job_name, ...)

    @staticmethod
    def rtc(job_name: str, granule: str, ..., kwargs) -> BaseJob:
        """Make an RTC Job object

        Args:
            job_name: A name for the job (must be <= 20 characters)
            granule: The granule (scene) to process
            extra_parameters: Extra job parameters specifying custom processing options

        Returns:
            A Job object
        """
        # TODO: warn about unsupported kwargs

    @staticmethod
    def insar(job_name: str, granule1: str, granule2: str, ..., kwargs) -> BaseJob:
        """Make an InSAR Job object

        Args:
            job_name: A name for the job (must be <= 20 characters)
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            extra_parameters: Extra job parameters specifying custom processing options

        Returns:
            A Job object
        """
        # TODO: warn about unsupported kwargs


class RequestedJob(BaseJob):
    id =
    product_files =

    def is_complete(self, wait: bool = False, timeout: int = 10800, check_every: int = 60) -> bool:
        # FIXME: side affect update when complete?

    def is_expired(self) -> bool:

    def _update_instance_data(self, response: dict):

    def download_files(self):