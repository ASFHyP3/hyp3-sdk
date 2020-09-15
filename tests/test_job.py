import pytest


from hyp3_sdk import Job, make_autorift_job, make_insar_gamma_job, make_rtc_gamma_job
from hyp3_sdk.exceptions import ValidationError


def test_job_validation_good_job():
    test_job = Job('RTC_GAMMA', 'job_name')
    assert test_job is not None
    assert test_job.job_name == 'job_name'
    assert test_job.job_parameters == {}
    assert test_job.job_type == 'RTC_GAMMA'

    with pytest.raises(ValidationError) as exec_info:
        Job('RTC_GAMMA', 'x' * 21,)
        assert 'Job name too long, must be less then 20 chars' == str(exec_info.value)

    with pytest.raises(ValidationError) as exec_info:
        Job('non-existant-job-type', 'job_name')
        assert 'Invalid job type: non-existant-job-type' in str(exec_info.value)


def test_job_to_dict():
    test_job = Job('RTC_GAMMA', 'job_name', {'param1': 'val1', 'param2': 'val2'})
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'RTC_GAMMA',
        'job_parameters': {
            'param1': 'val1',
            'param2': 'val2',
        }
    }


def test_make_rtc_gamma_job():
    test_job = make_rtc_gamma_job('job_name', 'granule_name')
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'RTC_GAMMA',
        'job_parameters': {
            'granules': ['granule_name'],
        }
    }

    test_job = make_rtc_gamma_job('job_name', 'granule_name', extra_parameters={'param1': 'val1'})
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'RTC_GAMMA',
        'job_parameters': {
            'granules': ['granule_name'],
            'param1': 'val1',
        }
    }


def test_make_insar_gamma_job():
    test_job = make_insar_gamma_job('job_name', 'granule1_name', 'granule2_name')
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'INSAR_GAMMA',
        'job_parameters': {
            'granules': ['granule1_name', 'granule2_name'],
        }
    }

    test_job = make_insar_gamma_job('job_name', 'granule1_name', 'granule2_name', extra_parameters={'param1': 'val1'})
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'INSAR_GAMMA',
        'job_parameters': {
            'granules': ['granule1_name', 'granule2_name'],
            'param1': 'val1',
        }
    }


def test_make_autorift_job():
    test_job = make_autorift_job('job_name', 'granule1_name', 'granule2_name')
    assert test_job.to_dict() == {
        'name': 'job_name',
        'job_type': 'AUTORIFT',
        'job_parameters': {
            'granules': ['granule1_name', 'granule2_name'],
        }
    }
