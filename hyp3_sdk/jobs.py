"""helper functions for making jobs to submit to the api"""
from hyp3_sdk.exceptions import ValidationError

JOB_TYPES = [
    'RTC_GAMMA',
    'INSAR_GAMMA',
    'AUTORIFT'
]


class Job:
    def __init__(self, job_type: str, job_name: str, job_parameters: dict = {}):
        if job_type not in JOB_TYPES:
            raise ValidationError(f'Invalid job type: {job_type}, must be one of {JOB_TYPES}')
        if len(job_name) > 20:
            raise ValidationError('Job name too long, must be less then 20 chars')
        self.job_name = job_name
        self.job_type = job_type
        self.job_parameters = job_parameters

    def to_dict(self) -> dict:
        return {
            'job_parameters': {
                **self.job_parameters
            },
            'job_type': self.job_type,
            'name': self.job_name,
        }


def make_job(job_type: str, job_name: str, job_parameters: dict) -> Job:
    return Job(job_type, job_name, job_parameters)


def make_autorift_job(job_name: str, granule1: str, granule2: str) -> Job:
    return Job('AUTORIFT', job_name, {'granules': [granule1, granule2]})


def make_rtc_gamma_job(job_name: str, granule: str, extra_parameters: dict = {}) -> Job:
    return Job('RTC_GAMMA', job_name, {'granules': [granule], **extra_parameters})


def make_insar_gamma_job(job_name: str, granule1: str, granule2: str, extra_parameters: dict = {}) -> Job:
    return Job('INSAR_GAMMA', job_name, {'granules': [granule1, granule2], **extra_parameters})
