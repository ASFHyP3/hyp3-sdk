from copy import copy
from datetime import datetime, timedelta

import pytest
import responses
from dateutil import tz

from hyp3_sdk.exceptions import HyP3SDKError
from hyp3_sdk.jobs import Batch, Job

SUCCEEDED_JOB = {
    "browse_images": ["https://PAIR_PROCESS.png"],
    "expiration_time": "2020-10-08T00:00:00+00:00",
    "files": [{"filename": "PAIR_PROCESS.nc", "size": 5949932, "url": "https://PAIR_PROCESS.nc"}],
    "logs": ["https://d1c05104-b455-4f35-a95a-84155d63f855.log"],
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
    "logs": ["https://281b2087-9e7d-4d17-a9b3-aebeb2ad23c6.log"],
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


def test_job_attributes():
    job = Job.from_dict(SUCCEEDED_JOB)
    for key in SUCCEEDED_JOB.keys():
        assert job.__getattribute__(key)

    job = Job.from_dict(FAILED_JOB)
    for key in FAILED_JOB.keys():
        assert job.__getattribute__(key)

    unprovided_attributes = set(vars(job).keys()) - set(FAILED_JOB.keys())
    for key in unprovided_attributes:
        assert job.__getattribute__(key) is None


def test_job_dict_transforms():
    job = Job.from_dict(SUCCEEDED_JOB)
    assert job.to_dict() == SUCCEEDED_JOB

    retry = job.to_dict(for_resubmit=True)
    assert retry.keys() == Job._attributes_for_resubmit

    job = Job.from_dict(FAILED_JOB)
    assert job.to_dict() == FAILED_JOB

    retry = job.to_dict(for_resubmit=True)
    assert retry.keys() == Job._attributes_for_resubmit


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

    with pytest.raises(HyP3SDKError) as execinfo:
        job = Job.from_dict(FAILED_JOB)
        job.expired()
        assert 'Only SUCCEEDED jobs have an expiration time' in str(execinfo.value)


@responses.activate
def test_job_download_files(tmp_path, get_mock_job):
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    job = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                       files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])
    responses.add(responses.GET, 'https://foo.com/file', body='foobar')

    path = job.download_files(tmp_path)[0]
    contents = path.read_text()
    assert path == tmp_path / 'file'
    assert contents == 'foobar'

    job = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                       files=[{'url': 'https://foo.com/f1', 'size': 0, 'filename': 'f1'}])
    responses.add(responses.GET, 'https://foo.com/f1', body='foobar1')

    path = job.download_files(str(tmp_path))[0]
    contents = path.read_text()
    assert path == tmp_path / 'f1'
    assert contents == 'foobar1'


@responses.activate
def test_job_download_files_create_dirs(tmp_path, get_mock_job):
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    job = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                       files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])

    with pytest.raises(NotADirectoryError):
        job.download_files(tmp_path / 'not_a_dir', create=False)

    responses.add(responses.GET, 'https://foo.com/file', body='foobar')
    path = job.download_files(tmp_path / 'not_a_dir', create=True)[0]
    contents = path.read_text()
    assert path == tmp_path / 'not_a_dir' / 'file'
    assert contents == 'foobar'


@responses.activate
def test_job_download_files_expired(tmp_path, get_mock_job):
    expired_time = (datetime.now(tz=tz.UTC) - timedelta(days=7)).isoformat(timespec='seconds')
    job = get_mock_job(status_code='SUCCEEDED', expiration_time=expired_time,
                       files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])

    with pytest.raises(HyP3SDKError):
        job.download_files(tmp_path)


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


def test_batch_iadd():
    a = Batch([Job.from_dict(SUCCEEDED_JOB)])
    b = Batch([Job.from_dict(FAILED_JOB)])
    j = Job.from_dict(SUCCEEDED_JOB)
    j.status_code = 'RUNNING'

    a += b
    assert len(a) == 2
    assert a.jobs[0].succeeded()
    assert a.jobs[1].failed()

    a += j
    assert len(a) == 3
    assert a.jobs[0].succeeded()
    assert a.jobs[1].failed()
    assert a.jobs[2].running()


def test_batch_iter():
    defined_jobs = [Job.from_dict(SUCCEEDED_JOB), Job.from_dict(FAILED_JOB)]
    batch = Batch(defined_jobs)
    for batch_job, defined_job in zip(batch, defined_jobs):
        assert batch_job == defined_job


def test_batch_len():
    batch = Batch()
    assert len(batch) == 0

    batch = Batch([])
    assert len(batch) == 0

    batch = Batch([Job.from_dict(SUCCEEDED_JOB), Job.from_dict(FAILED_JOB)])
    assert len(batch) == 2


def test_contains(get_mock_job):
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    j1 = Job.from_dict(SUCCEEDED_JOB)
    j2 = Job.from_dict(FAILED_JOB)
    j3 = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                      files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])

    a = Batch([j1, j2])

    assert j1 in a
    assert j2 in a
    assert j3 not in a


def test_delitem():
    j1 = Job.from_dict(SUCCEEDED_JOB)
    j2 = Job.from_dict(FAILED_JOB)
    batch = Batch([j1, j2])

    assert j1 in batch
    assert j2 in batch

    del batch[1]

    assert j1 in batch
    assert j2 not in batch

    batch += j2
    del batch[0]

    assert j1 not in batch
    assert j2 in batch


def test_getitem():
    j1 = Job.from_dict(SUCCEEDED_JOB)
    j2 = Job.from_dict(FAILED_JOB)
    batch = Batch([j1, j2])

    assert j1 == batch[0]
    assert j2 == batch[1]


def test_setitem(get_mock_job):
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    j1 = Job.from_dict(SUCCEEDED_JOB)
    j2 = Job.from_dict(FAILED_JOB)
    j3 = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                      files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])
    batch = Batch([j1, j2])

    batch[1] = j3
    assert batch[1] == j3


def test_reverse(get_mock_job):
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    j1 = Job.from_dict(SUCCEEDED_JOB)
    j2 = Job.from_dict(FAILED_JOB)
    j3 = get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                      files=[{'url': 'https://foo.com/file', 'size': 0, 'filename': 'file'}])

    batch = Batch([j1, j2, j3])

    batch_reversed = list(reversed(batch))

    assert batch_reversed[0] == j3
    assert batch_reversed[1] == j2
    assert batch_reversed[2] == j1


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
    expiration_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    batch = Batch([
        get_mock_job(status_code='SUCCEEDED', expiration_time=expiration_time,
                     files=[{'url': 'https://foo.com/file1', 'size': 0, 'filename': 'file1'}]),
        get_mock_job(status_code='SUCCEEDED', expiration_time=expiration_time,
                     files=[{'url': 'https://foo.com/file2', 'size': 0, 'filename': 'file2'}]),
        get_mock_job(status_code='SUCCEEDED', expiration_time=expiration_time,
                     files=[{'url': 'https://foo.com/file3', 'size': 0, 'filename': 'file3'}])
    ])
    responses.add(responses.GET, 'https://foo.com/file1', body='foobar1')
    responses.add(responses.GET, 'https://foo.com/file2', body='foobar2')
    responses.add(responses.GET, 'https://foo.com/file3', body='foobar3')

    paths = batch.download_files(tmp_path)
    contents = [path.read_text() for path in paths]
    assert len(paths) == 3
    assert set(paths) == {tmp_path / 'file1', tmp_path / 'file2', tmp_path / 'file3'}
    assert set(contents) == {'foobar1', 'foobar2', 'foobar3'}

    with pytest.raises(NotADirectoryError):
        batch.download_files(tmp_path / 'not_a_dir', create=False)

    paths = batch.download_files(tmp_path / 'not_a_dir', create=True)
    contents = [path.read_text() for path in paths]
    assert len(paths) == 3
    assert set(paths) == {tmp_path / 'not_a_dir' / 'file1',
                          tmp_path / 'not_a_dir' / 'file2',
                          tmp_path / 'not_a_dir' / 'file3'}
    assert set(contents) == {'foobar1', 'foobar2', 'foobar3'}


@responses.activate
def test_batch_download_expired(tmp_path, get_mock_job):
    expired_time = (datetime.now(tz=tz.UTC) - timedelta(days=7)).isoformat(timespec='seconds')
    unexpired_time = (datetime.now(tz=tz.UTC) + timedelta(days=7)).isoformat(timespec='seconds')
    batch = Batch([
        get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                     files=[{'url': 'https://foo.com/file1', 'size': 0, 'filename': 'file1'}]),
        get_mock_job(status_code='SUCCEEDED', expiration_time=expired_time,
                     files=[{'url': 'https://foo.com/file2', 'size': 0, 'filename': 'file2'}]),
        get_mock_job(status_code='SUCCEEDED', expiration_time=unexpired_time,
                     files=[{'url': 'https://foo.com/file3', 'size': 0, 'filename': 'file3'}])
    ])
    responses.add(responses.GET, 'https://foo.com/file1', body='foobar1')
    responses.add(responses.GET, 'https://foo.com/file2', body='foobar2')
    responses.add(responses.GET, 'https://foo.com/file3', body='foobar3')

    paths = batch.download_files(tmp_path)
    contents = [path.read_text() for path in paths]
    assert len(paths) == 2
    assert set(paths) == {tmp_path / 'file1', tmp_path / 'file3'}
    assert set(contents) == {'foobar1', 'foobar3'}


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
