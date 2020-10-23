from hyp3_sdk.exceptions import ValidationError

JOB_TYPES = [
    'RTC_GAMMA',
    'INSAR_GAMMA',
    'AUTORIFT'
]


class Job:
    """Jobs to be submitted to the API"""
    def __init__(self, job_type: str, job_name: str, job_parameters: dict = {}):
        """Create a new Job object

        Args:
            job_type: The job type
            job_name: A name for the job (must be <= 20 characters)
            job_parameters: Extra job parameters specifying custom processing options
        """
        if job_type not in JOB_TYPES:
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


def make_job(job_type: str, job_name: str, job_parameters: dict = {}) -> Job:
    """Make a generic Job object

    Args:
        job_type: The job type
        job_name: A name for the job (must be <= 20 characters)
        job_parameters: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return Job(job_type, job_name, job_parameters)


def make_autorift_job(job_name: str, granule1: str, granule2: str) -> Job:
    """Make an autoRIFT Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule1: The first granule (scene) to use
        granule2: The second granule (scene) to use

    Returns:
        A Job object
    """
    return Job('AUTORIFT', job_name, {'granules': [granule1, granule2]})


def make_rtc_gamma_job(job_name: str, granule: str, extra_parameters: dict = {}) -> Job:
    """Make an RTC Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule: The granule (scene) to process
        extra_parameters: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return Job('RTC_GAMMA', job_name, {'granules': [granule], **extra_parameters})


def make_insar_gamma_job(job_name: str, granule1: str, granule2: str, extra_parameters: dict = {}) -> Job:
    """Make an InSAR Job object

    Args:
        job_name: A name for the job (must be <= 20 characters)
        granule1: The first granule (scene) to use
        granule2: The second granule (scene) to use
        extra_parameters: Extra job parameters specifying custom processing options

    Returns:
        A Job object
    """
    return Job('INSAR_GAMMA', job_name, {'granules': [granule1, granule2], **extra_parameters})
