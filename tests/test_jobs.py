from copy import copy
from datetime import datetime, timedelta

import pytest
import responses
from dateutil import tz

from hyp3_sdk.exceptions import HyP3Error
from hyp3_sdk.jobs import Batch, Job

SUCCEEDED_JOB = {
    "browse_images": ["https://PAIR_PROCESS.png"],
    "expiration_time": "2020-10-08T00:00:00+00:00",
    "files": [{"filename": "PAIR_PROCESS.nc", "size": 5949932, "url": "https://PAIR_PROCESS.nc"}],
    "job_id": "d1c05104-b455-4f35-a95a-84155d63f855",
    "job_parameters": {"granules": [
        "S1A_IW_SLC__1SDH_20180511T204719_20180511T204746_021862_025C12_6F77",
        "S1B_IW_SLC__1SDH_20180505T204637_20180505T204704_010791_013B91_E42D"
    ]},
    "job_type": "PAIR_PROCESS",
    "name": "test_success",
    "request_time": "2020-09-22T23:55:10+00:00",
    "status_code": "SUCCEEDED",
    "thumbnail_images": ["https://PAIR_PROCESS_thumb.png"],
    "user_id": "asf_hyp3"
}

FAILED_JOB = {
    "job_id": "281b2087-9e7d-4d17-a9b3-aebeb2ad23c6",
    "job_parameters": {
        "granules": [
            "S1A_IW_SLC__1SSH_20161126T080144_20161126T080211_014110_016C51_037E",
            "S1B_IW_SLC__1SSH_20161120T080102_20161120T080129_003039_0052AE_AA91"
        ]
    },
    "job_type": "PAIR_PROCESS",
    "name": "test_failure",
    "request_time": "2020-09-22T23:55:10+00:00",
    "status_code": "FAILED",
    "user_id": "asf_hyp3"
}


def test_job_dict_transforms():
    job = Job.from_dict(SUCCEEDED_JOB)
    assert job.to_dict() == SUCCEEDED_JOB

    job = Job.from_dict(FAILED_JOB)
    assert job.to_dict() == FAILED_JOB


def test_job_complete_succeeded_failed_running():
    job = Job.from_dict(SUCCEEDED_JOB)
    assert job.complete()
    assert job.succeeded()
    assert not job.failed()
    assert not job.running()

    job = Job.from_dict(FAILED_JOB)
    assert job.complete()
    assert not job.succeeded()
    assert job.failed()
    assert not job.running()

    job.status_code = 'PENDING'
    assert not job.complete()
    assert not job.succeeded()
    assert not job.failed()
    assert job.running()

    job.status_code = 'RUNNING'
    assert not job.complete()
    assert not job.succeeded()
    assert not job.failed()
    assert job.running()


def test_job_expired():
    job = Job.from_dict(SUCCEEDED_JOB)
    job.expiration_time = datetime.now(tz.UTC) + timedelta(days=7)
    assert not job.expired()

    job.expiration_time = datetime.now(tz.UTC) - timedelta(days=7)
    assert job.expired()

    with pytest.raises(HyP3Error) as execinfo:
        job = Job.from_dict(FAILED_JOB)
        job.expired()
        assert 'Only SUCCEEDED jobs have an expiration time' in str(execinfo.value)


@responses.activate
def test_job_download_files(tmp_path, get_mock_job):
    job = get_mock_job(status_code='SUCCEEDED', files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])
    responses.add(responses.GET, 'https://foo.com/file', body='foobar')

    path = job.download_files(tmp_path)[0]
    contents = path.read_text()
    assert path == tmp_path / 'file'
    assert contents == 'foobar'


def test_batch_len():
    with pytest.warns(UserWarning):
        batch = Batch([])
    assert len(batch) == 0

    batch = Batch([Job.from_dict(SUCCEEDED_JOB), Job.from_dict(FAILED_JOB)])
    assert len(batch) == 2


def test_batch_add():
    a = Batch([Job.from_dict(SUCCEEDED_JOB)])
    b = Batch([Job.from_dict(FAILED_JOB)])
    j = Job.from_dict(SUCCEEDED_JOB)
    j.status_code = 'RUNNING'

    c = a + b
    assert len(c) == 2
    assert c.jobs[0].succeeded()
    assert c.jobs[1].failed()

    d = c + j
    assert len(d) == 3
    assert d.jobs[0].succeeded()
    assert d.jobs[1].failed()
    assert d.jobs[2].running()


def test_batch_complete_succeeded():
    batch = Batch([Job.from_dict(SUCCEEDED_JOB), Job.from_dict(SUCCEEDED_JOB)])
    assert batch.complete()
    assert batch.succeeded()

    batch += Job.from_dict(FAILED_JOB)
    assert batch.complete()
    assert not batch.succeeded()

    running = Job.from_dict(FAILED_JOB)
    running.status_code = 'RUNNING'
    batch += running
    assert not batch.complete()
    assert not batch.succeeded()


@responses.activate
def test_batch_download(tmp_path, get_mock_job):
    batch = Batch([
        get_mock_job(status_code='SUCCEEDED', files=[{'url': 'https://foo.com/file1', 'size': 0, 'filename': 'file1'}]),
        get_mock_job(status_code='SUCCEEDED', files=[{'url': 'https://foo.com/file2', 'size': 0, 'filename': 'file2'}]),
        get_mock_job(status_code='SUCCEEDED', files=[{'url': 'https://foo.com/file3', 'size': 0, 'filename': 'file3'}])
    ])
    responses.add(responses.GET, 'https://foo.com/file1', body='foobar1')
    responses.add(responses.GET, 'https://foo.com/file2', body='foobar2')
    responses.add(responses.GET, 'https://foo.com/file3', body='foobar3')

    paths = batch.download_files(tmp_path)
    contents = [path.read_text() for path in paths]
    assert len(paths) == 3
    assert set(paths) == {tmp_path / 'file1', tmp_path / 'file2', tmp_path / 'file3'}
    assert set(contents) == {'foobar1', 'foobar2', 'foobar3'}


def test_batch_any_expired():
    job1 = Job.from_dict(SUCCEEDED_JOB)
    job1.expiration_time = datetime.now(tz.UTC) + timedelta(days=7)

    job2 = copy(job1)
    job2.expiration_time = datetime.now(tz.UTC) + timedelta(days=2)

    batch = Batch([job1, job2])
    assert not batch.any_expired()

    # ignore jobs without expiration times
    job3 = Job.from_dict(FAILED_JOB)
    batch += job3
    assert not batch.any_expired()

    job4 = copy(job1)
    job4.expiration_time = datetime.now(tz.UTC) - timedelta(days=2)
    batch += job4
    assert batch.any_expired()


def test_batch_filter_jobs():
    succeeded_job = Job.from_dict(SUCCEEDED_JOB)
    succeeded_job.expiration_time = datetime.now(tz.UTC) + timedelta(days=7)

    expired_job = Job.from_dict(SUCCEEDED_JOB)
    expired_job.expiration_time = datetime.now(tz.UTC) - timedelta(days=7)

    running_job = Job.from_dict(FAILED_JOB)
    running_job.status_code = 'RUNNING'

    pending_job = Job.from_dict(FAILED_JOB)
    pending_job.status_code = 'PENDING'

    batch = Batch([succeeded_job, running_job, expired_job, pending_job, Job.from_dict(FAILED_JOB)])

    not_failed = batch.filter_jobs()
    assert len(not_failed) == 4
    assert not_failed.jobs[0].succeeded() and not not_failed.jobs[0].expired()
    assert not_failed.jobs[1].running()
    assert not_failed.jobs[2].succeeded() and not_failed.jobs[2].expired()
    assert not_failed.jobs[3].running()

    not_failed_or_expired = batch.filter_jobs(include_expired=False)
    assert len(not_failed_or_expired) == 3
    assert not_failed_or_expired.jobs[0].succeeded() and not not_failed_or_expired.jobs[0].expired()
    assert not_failed_or_expired.jobs[1].running()
    assert not_failed_or_expired.jobs[2].running()

    succeeded = batch.filter_jobs(running=False)
    assert len(succeeded) == 2
    assert succeeded.jobs[0].succeeded() and not succeeded.jobs[0].expired()
    assert succeeded.jobs[1].succeeded() and succeeded.jobs[1].expired()

    running = batch.filter_jobs(succeeded=False)
    assert len(running) == 2
    assert running.jobs[0].running()
    assert running.jobs[1].running()

    failed = batch.filter_jobs(succeeded=False, running=False, failed=True)
    assert len(failed) == 1
    assert failed.jobs[0].failed()

    everything = batch.filter_jobs(failed=True)
    assert len(everything) == len(batch)
    for ii, job in enumerate(everything.jobs):
        assert job.status_code == batch.jobs[ii].status_code
        if job.succeeded():
            assert job.expired() == batch.jobs[ii].expired()
