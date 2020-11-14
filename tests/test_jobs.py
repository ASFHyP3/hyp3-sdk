from hyp3_sdk.jobs import Job


def test_job_from_dict():
    assert False


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


def test_job_complete():
    assert False


def test_job_expired():
    assert False


def test_job_download_files():
    assert False


def test_batch_add():
    assert False


def test_batch_complete():
    assert False


def test_batch_download():
    assert False


def test_batch_any_expired():
    assert False


def test_batch_drop_expired():
    assert False
