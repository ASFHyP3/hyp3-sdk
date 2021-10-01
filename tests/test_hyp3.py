import warnings
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

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

    batch = api.find_jobs()
    assert len(batch) == 0


@responses.activate
def test_find_jobs_paging(get_mock_job):
    api = HyP3()
    api_response_mock_1 = {
        'jobs': [
            get_mock_job(name='job1').to_dict(),
            get_mock_job(name='job2').to_dict(),
        ],
        'next': urljoin(api.url, '/jobs?next=foobar')
    }
    api_response_mock_2 = {
        'jobs': [
            get_mock_job(name='job3').to_dict()
        ]
    }

    responses.add(responses.GET, urljoin(api.url, '/jobs'), json=api_response_mock_1, match_querystring=True)
    responses.add(responses.GET, urljoin(api.url, '/jobs?next=foobar'),  json=api_response_mock_2)

    batch = api.find_jobs()
    assert len(batch) == 3
    assert 'next' not in responses.calls[0].request.params
    assert 'next' in responses.calls[1].request.params


@responses.activate
def test_find_jobs_start():
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/jobs?start=2021-01-01T00%3A00%3A00%2B00%3A00'),
                  json={'jobs': []}, match_querystring=True)

    batch = api.find_jobs(start=datetime(2021, 1, 1))
    assert len(batch) == 0

    batch = api.find_jobs(start=datetime(2021, 1, 1, tzinfo=timezone.utc))
    assert len(batch) == 0


@responses.activate
def test_find_jobs_end():
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, '/jobs?end=2021-01-02T00%3A00%3A00%2B00%3A00'),
                  json={'jobs': []}, match_querystring=True)

    batch = api.find_jobs(end=datetime(2021, 1, 2))
    assert len(batch) == 0

    batch = api.find_jobs(end=datetime(2021, 1, 2, tzinfo=timezone.utc))
    assert len(batch) == 0


@responses.activate
def test_find_jobs_status_code():
    api = HyP3()

    responses.add(responses.GET, urljoin(api.url, '/jobs?status_code=RUNNING'),
                  json={'jobs': []}, match_querystring=True)
    batch = api.find_jobs(status_code='RUNNING')
    assert len(batch) == 0

    responses.add(responses.GET, urljoin(api.url, '/jobs?status_code=FAILED'),
                  json={'jobs': []}, match_querystring=True)
    batch = api.find_jobs(status_code='FAILED')
    assert len(batch) == 0


@responses.activate
def test_get_job_by_id(get_mock_job):
    job = get_mock_job()
    api = HyP3()
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{job.job_id}'), json=job.to_dict())
    response = api.get_job_by_id(job.job_id)
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
def test_submit_prepared_jobs(get_mock_job):
    rtc_job = get_mock_job('RTC_GAMMA', job_parameters={'granules': ['g1']})
    insar_job = get_mock_job('INSAR_GAMMA', job_parameters={'granules': ['g1', 'g2']})
    api_response = {
        'jobs': [
            rtc_job.to_dict(),
            insar_job.to_dict(),
        ]
    }

    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)

    batch = api.submit_prepared_jobs(
        [rtc_job.to_dict(for_resubmit=True), insar_job.to_dict(for_resubmit=True)])
    assert batch.jobs == [rtc_job, insar_job]


def test_prepare_autorift_job():
    assert HyP3.prepare_autorift_job(granule1='my_granule1', granule2='my_granule2') == {
        'job_type': 'AUTORIFT',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
        }
    }
    assert HyP3.prepare_autorift_job(granule1='my_granule1',  granule2='my_granule2', name='my_name') == {
        'job_type': 'AUTORIFT',
        'name': 'my_name',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
        },
    }


def test_prepare_rtc_job():
    assert HyP3.prepare_rtc_job(granule='my_granule') == {
        'job_type': 'RTC_GAMMA',
        'job_parameters': {
            'granules': ['my_granule'],
            'dem_matching': False,
            'include_dem': False,
            'include_inc_map': False,
            'include_rgb': False,
            'include_scattering_area': False,
            'radiometry': 'gamma0',
            'resolution': 30,
            'scale': 'power',
            'speckle_filter': False,
            'dem_name': 'copernicus',
        }
    }
    assert HyP3.prepare_rtc_job(granule='my_granule', name='my_name') == {
        'job_type': 'RTC_GAMMA',
        'name': 'my_name',
        'job_parameters': {
            'granules': ['my_granule'],
            'dem_matching': False,
            'include_dem': False,
            'include_inc_map': False,
            'include_rgb': False,
            'include_scattering_area': False,
            'radiometry': 'gamma0',
            'resolution': 30,
            'scale': 'power',
            'speckle_filter': False,
            'dem_name': 'copernicus',
        },
    }


def test_prepare_insar_job():
    assert HyP3.prepare_insar_job(granule1='my_granule1', granule2='my_granule2') == {
        'job_type': 'INSAR_GAMMA',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
            'include_look_vectors': False,
            'include_los_displacement': False,
            'include_inc_map': False,
            'looks': '20x4',
            'include_dem': False,
            'include_wrapped_phase': False,
            'apply_water_mask': False,
            'include_displacement_maps': False,
        }
    }
    assert HyP3.prepare_insar_job(granule1='my_granule1',  granule2='my_granule2', name='my_name', looks='10x2',
                                  include_los_displacement=True, include_look_vectors=True, include_inc_map=True,
                                  include_dem=True, include_wrapped_phase=True, apply_water_mask=True,
                                  include_displacement_maps=True) == {
        'job_type': 'INSAR_GAMMA',
        'name': 'my_name',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
            'include_look_vectors': True,
            'include_los_displacement': True,
            'include_inc_map': True,
            'looks': '10x2',
            'include_dem': True,
            'include_wrapped_phase': True,
            'apply_water_mask': True,
            'include_displacement_maps': True,
        },
    }


def test_deprecated_warning():
    with warnings.catch_warnings(record=True) as w:
        HyP3.prepare_insar_job(granule1='my_granule1', granule2='my_granule2', include_los_displacement=False)
        assert len(w) == 0

    with warnings.catch_warnings(record=True) as w:
        HyP3.prepare_insar_job(granule1='my_granule1', granule2='my_granule2', include_los_displacement=True)
        assert len(w) == 1
        assert issubclass(w[0].category, FutureWarning)
        assert 'deprecated' in str(w[0].message)


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
    batch = api.submit_autorift_job('g1', 'g2')
    assert batch.jobs[0] == job


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
    batch = api.submit_rtc_job('g1')
    assert batch.jobs[0] == job


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
    batch = api.submit_insar_job('g1', 'g2')
    assert batch.jobs[0] == job


@responses.activate
def test_resubmit_previous_job(get_mock_job):
    job = get_mock_job()
    api_response = {
        'jobs': [
            job.to_dict()
        ]
    }
    api = HyP3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_prepared_jobs(job.to_dict(for_resubmit=True))
    assert batch.jobs[0] == job


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
