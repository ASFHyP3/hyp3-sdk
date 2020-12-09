from datetime import datetime, timedelta
from urllib.parse import urljoin

import pytest
import responses

import hyp3_sdk
from hyp3_sdk import HyP3, Job

hyp3_sdk.TESTING = True


@responses.activate
def test_session_headers():
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/user'), json={'foo': 'bar'})

    api.session.get(urljoin(api.url, '/user'))
    assert responses.calls[0].request.headers['User-Agent'] == f'hyp3_sdk/{hyp3_sdk.__version__}'

    api.my_info()
    assert responses.calls[1].request.headers['User-Agent'] == f'hyp3_sdk/{hyp3_sdk.__version__}'


@responses.activate
def test_find_jobs(get_mock_job):
    api_response_mock = {
        'jobs': [
            get_mock_job(name='job1').to_dict(),
            get_mock_job(name='job2', request_time=datetime.now() - timedelta(minutes=15)).to_dict(),
            get_mock_job(name='job3', status_code='SUCCEEDED',
                         files=[{'url': 'https://foo.com/file.zip', 'size': 1000, 'filename': 'file.zip'}],
                         browse_images=['https://foo.com/browse.png'],
                         thumbnail_images=['https://foo.com/thumbnail.png']).to_dict()
        ]
    }

    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/jobs'), json=api_response_mock)
    responses.add(responses.GET, urljoin(api.url, '/jobs'), json={'jobs': []})

    batch = api.find_jobs()
    assert len(batch) == 3

    with pytest.warns(UserWarning):
        batch = api.find_jobs()
    assert len(batch) == 0


@responses.activate
def test_get_job_by_id(get_mock_job):
    job = get_mock_job()
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{job.job_id}'), json=job.to_dict())
    response = api._get_job_by_id(job.job_id)
    assert response == job


@responses.activate
def test_watch(get_mock_job):
    incomplete_job = get_mock_job()
    complete_job = Job.from_dict(incomplete_job.to_dict())
    complete_job.status_code = 'SUCCEEDED'
    api = HyP3()
    for ii in range(3):
        responses.add(responses.GET, urljoin(api.url, f'/jobs/{incomplete_job.job_id}'),
                      json=incomplete_job.to_dict())
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{incomplete_job.job_id}'),
                  json=complete_job.to_dict())
    response = api.watch(incomplete_job, interval=0.05)
    assert response == complete_job
    responses.assert_call_count(urljoin(api.url, f'/jobs/{incomplete_job.job_id}'), 4)


@responses.activate
def test_refresh(get_mock_job):
    job = get_mock_job()
    new_job = Job.from_dict(job.to_dict())
    new_job.status_code = 'SUCCEEDED'

    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{job.job_id}'), json=new_job.to_dict())
    response = api.refresh(job)
    assert response == new_job


@responses.activate
def test_submit_job_dict(get_mock_job):
    job = get_mock_job()
    api_response = {
        'jobs': [
            job.to_dict()
        ]
    }
    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    response = api.submit_job_dict(job.to_dict(for_resubmit=True))
    assert response == job


@responses.activate
def test_submit_autorift_job(get_mock_job):
    job = get_mock_job('AUTORIFT', job_parameters={'granules': ['g1', 'g2']})
    api_response = {
        'jobs': [
            job.to_dict()
        ]
    }
    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    response = api.submit_autorift_job('g1', 'g2')
    assert response == job


@responses.activate
def test_submit_rtc_job(get_mock_job):
    job = get_mock_job('RTC_GAMMA', job_parameters={'granules': ['g1']})
    api_response = {
        'jobs': [
            job.to_dict()
        ]
    }
    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    response = api.submit_rtc_job('g1')
    assert response == job


@responses.activate
def test_submit_insar_job(get_mock_job):
    job = get_mock_job('INSAR_GAMMA', job_parameters={'granules': ['g1', 'g2']})
    api_response = {
        'jobs': [
            job.to_dict()
        ]
    }
    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    response = api.submit_insar_job('g1', 'g2')
    assert response == job


@responses.activate
def test_my_info():
    api_response = {
        'job_names': [
            'name1',
            'name2'
        ],
        'quota': {
            'max_job_per_month': 50,
            'remaining': 25
        },
        'user_id': 'someUser'
    }
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/user'), json=api_response)
    response = api.my_info()
    assert response == api_response


@responses.activate
def test_check_quota():
    api_response = {
        'job_names': [
            'name1',
            'name2'
        ],
        'quota': {
            'max_job_per_month': 50,
            'remaining': 25
        },
        'user_id': 'someUser'
    }
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/user'), json=api_response)
    response = api.check_quota()
    assert response == api_response['quota']['remaining']
