import math
import warnings
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

import pytest
import responses

import hyp3_sdk
from hyp3_sdk import Batch, HyP3, Job
from hyp3_sdk.exceptions import HyP3Error


@responses.activate
def test_session_headers(get_mock_hyp3):
    api = get_mock_hyp3()

    responses.add(responses.GET, urljoin(api.url, '/user'), json={'foo': 'bar'})

    api.session.get(urljoin(api.url, '/user'))
    assert responses.calls[0].request.headers['User-Agent'] == f'hyp3_sdk/{hyp3_sdk.__version__}'

    api.my_info()
    assert responses.calls[1].request.headers['User-Agent'] == f'hyp3_sdk/{hyp3_sdk.__version__}'


@responses.activate
def test_find_jobs(get_mock_hyp3, get_mock_job):
    api_response_mock = {
        'jobs': [
            get_mock_job(name='job1').to_dict(),
            get_mock_job(name='job2', request_time=datetime.now() - timedelta(minutes=15)).to_dict(),
            get_mock_job(
                name='job3',
                status_code='SUCCEEDED',
                files=[{'url': 'https://foo.com/file.zip', 'size': 1000, 'filename': 'file.zip'}],
                browse_images=['https://foo.com/browse.png'],
                thumbnail_images=['https://foo.com/thumbnail.png'],
            ).to_dict(),
        ]
    }

    api = get_mock_hyp3()

    responses.add(responses.GET, urljoin(api.url, '/jobs'), json=api_response_mock)
    responses.add(responses.GET, urljoin(api.url, '/jobs'), json={'jobs': []})

    batch = api.find_jobs()
    assert len(batch) == 3

    batch = api.find_jobs()
    assert len(batch) == 0


@responses.activate
def test_find_jobs_paging(get_mock_hyp3, get_mock_job):
    api = get_mock_hyp3()

    api_response_mock_1 = {
        'jobs': [
            get_mock_job(name='job1').to_dict(),
            get_mock_job(name='job2').to_dict(),
        ],
        'next': urljoin(api.url, '/jobs?next=foobar'),
    }
    api_response_mock_2 = {'jobs': [get_mock_job(name='job3').to_dict()]}

    responses.add(responses.GET, urljoin(api.url, '/jobs'), json=api_response_mock_1, match_querystring=True)
    responses.add(responses.GET, urljoin(api.url, '/jobs?next=foobar'), json=api_response_mock_2)

    batch = api.find_jobs()
    assert len(batch) == 3
    assert 'next' not in responses.calls[0].request.params  # type: ignore [attr-defined]
    assert 'next' in responses.calls[1].request.params  # type: ignore [attr-defined]


@responses.activate
def test_find_jobs_user_id(get_mock_hyp3, get_mock_job):
    api = get_mock_hyp3()

    responses.add(responses.GET, urljoin(api.url, '/jobs?user_id=foo'), json={'jobs': []}, match_querystring=True)

    responses.add(
        responses.GET,
        urljoin(api.url, '/jobs?user_id=bar'),
        json={'jobs': [get_mock_job(name='job1').to_dict()]},
        match_querystring=True,
    )

    batch = api.find_jobs(user_id='foo')
    assert len(batch) == 0

    batch = api.find_jobs(user_id='bar')
    assert len(batch) == 1


@responses.activate
def test_find_jobs_start(get_mock_hyp3):
    api = get_mock_hyp3()

    responses.add(
        responses.GET,
        urljoin(api.url, '/jobs?start=2021-01-01T00%3A00%3A00%2B00%3A00'),
        json={'jobs': []},
        match_querystring=True,
    )

    batch = api.find_jobs(start=datetime(2021, 1, 1))
    assert len(batch) == 0

    batch = api.find_jobs(start=datetime(2021, 1, 1, tzinfo=timezone.utc))
    assert len(batch) == 0


@responses.activate
def test_find_jobs_end(get_mock_hyp3):
    api = get_mock_hyp3()

    responses.add(
        responses.GET,
        urljoin(api.url, '/jobs?end=2021-01-02T00%3A00%3A00%2B00%3A00'),
        json={'jobs': []},
        match_querystring=True,
    )

    batch = api.find_jobs(end=datetime(2021, 1, 2))
    assert len(batch) == 0

    batch = api.find_jobs(end=datetime(2021, 1, 2, tzinfo=timezone.utc))
    assert len(batch) == 0


@responses.activate
def test_find_jobs_status_code(get_mock_hyp3):
    api = get_mock_hyp3()

    responses.add(
        responses.GET, urljoin(api.url, '/jobs?status_code=RUNNING'), json={'jobs': []}, match_querystring=True
    )
    batch = api.find_jobs(status_code='RUNNING')
    assert len(batch) == 0

    responses.add(
        responses.GET, urljoin(api.url, '/jobs?status_code=FAILED'), json={'jobs': []}, match_querystring=True
    )
    batch = api.find_jobs(status_code='FAILED')
    assert len(batch) == 0


@responses.activate
def test_get_job_by_id(get_mock_hyp3, get_mock_job):
    job = get_mock_job()
    api = get_mock_hyp3()
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{job.job_id}'), json=job.to_dict())
    response = api.get_job_by_id(job.job_id)
    assert response == job


@responses.activate
def test_watch(get_mock_hyp3, get_mock_job):
    incomplete_job = get_mock_job()
    complete_job = Job.from_dict(incomplete_job.to_dict())
    complete_job.status_code = 'SUCCEEDED'
    api = get_mock_hyp3()
    for ii in range(3):
        responses.add(responses.GET, urljoin(api.url, f'/jobs/{incomplete_job.job_id}'), json=incomplete_job.to_dict())
    responses.add(responses.GET, urljoin(api.url, f'/jobs/{incomplete_job.job_id}'), json=complete_job.to_dict())
    response = api.watch(incomplete_job, interval=0.05)
    assert response == complete_job
    responses.assert_call_count(urljoin(api.url, f'/jobs/{incomplete_job.job_id}'), 4)


@responses.activate
def test_refresh(get_mock_hyp3, get_mock_job):
    job = get_mock_job()
    new_job = Job.from_dict(job.to_dict())
    new_job.status_code = 'SUCCEEDED'

    api = get_mock_hyp3()

    responses.add(responses.GET, urljoin(api.url, f'/jobs/{job.job_id}'), json=new_job.to_dict())
    response = api.refresh(job)
    assert response == new_job


@responses.activate
def test_submit_prepared_jobs(get_mock_hyp3, get_mock_job):
    rtc_job = get_mock_job('RTC_GAMMA', job_parameters={'granules': ['g1']})
    insar_job = get_mock_job('INSAR_GAMMA', job_parameters={'granules': ['g1', 'g2']})
    api_response = {
        'jobs': [
            rtc_job.to_dict(),
            insar_job.to_dict(),
        ]
    }

    api = get_mock_hyp3()

    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)

    batch = api.submit_prepared_jobs([rtc_job.to_dict(for_resubmit=True), insar_job.to_dict(for_resubmit=True)])
    assert batch.jobs == [rtc_job, insar_job]


def test_prepare_autorift_job():
    assert HyP3.prepare_autorift_job(granule1='my_granule1', granule2='my_granule2') == {
        'job_type': 'AUTORIFT',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
        },
    }
    assert HyP3.prepare_autorift_job(granule1='my_granule1', granule2='my_granule2', name='my_name') == {
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
        },
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
            'phase_filter_parameter': 0.6,
        },
    }
    assert HyP3.prepare_insar_job(
        granule1='my_granule1',
        granule2='my_granule2',
        name='my_name',
        looks='10x2',
        include_los_displacement=True,
        include_look_vectors=True,
        include_inc_map=True,
        include_dem=True,
        include_wrapped_phase=True,
        apply_water_mask=True,
        include_displacement_maps=True,
        phase_filter_parameter=0.4,
    ) == {
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
            'phase_filter_parameter': 0.4,
        },
    }


def test_prepare_insar_isce_burst_job():
    assert HyP3.prepare_insar_isce_burst_job(granule1='my_granule1', granule2='my_granule2') == {
        'job_type': 'INSAR_ISCE_BURST',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
            'apply_water_mask': False,
            'looks': '20x4',
        },
    }
    assert HyP3.prepare_insar_isce_burst_job(
        granule1='my_granule1', granule2='my_granule2', name='my_name', apply_water_mask=True, looks='10x2'
    ) == {
        'job_type': 'INSAR_ISCE_BURST',
        'name': 'my_name',
        'job_parameters': {
            'granules': ['my_granule1', 'my_granule2'],
            'apply_water_mask': True,
            'looks': '10x2',
        },
    }


def test_prepare_insar_isce_multi_burst_job():
    assert HyP3.prepare_insar_isce_multi_burst_job(reference=['g1'], secondary=['g2']) == {
        'job_type': 'INSAR_ISCE_MULTI_BURST',
        'job_parameters': {
            'reference': ['g1'],
            'secondary': ['g2'],
            'apply_water_mask': False,
            'looks': '20x4',
        },
    }
    assert HyP3.prepare_insar_isce_multi_burst_job(
        reference=['g1', 'g2'], secondary=['g3', 'g4'], name='my_name', apply_water_mask=True, looks='10x2'
    ) == {
        'job_type': 'INSAR_ISCE_MULTI_BURST',
        'name': 'my_name',
        'job_parameters': {
            'reference': ['g1', 'g2'],
            'secondary': ['g3', 'g4'],
            'apply_water_mask': True,
            'looks': '10x2',
        },
    }


def test_prepare_opera_rtc_s1_job():
    assert HyP3.prepare_opera_rtc_s1_job(granule='g1') == {
        'job_type': 'OPERA_RTC_S1',
        'job_parameters': {
            'granules': ['g1'],
        },
    }
    assert HyP3.prepare_opera_rtc_s1_job(granule='g2', name='my_name') == {
        'job_type': 'OPERA_RTC_S1',
        'name': 'my_name',
        'job_parameters': {
            'granules': ['g2'],
        },
    }


def test_prepare_aria_s1_gunw_job():
    assert HyP3.prepare_aria_s1_gunw_job(reference_date='ref_date_1', secondary_date='sec_date_1', frame_id=100) == {
        'job_type': 'ARIA_S1_GUNW',
        'job_parameters': {
            'reference_date': 'ref_date_1',
            'secondary_date': 'sec_date_1',
            'frame_id': 100,
        },
    }
    assert HyP3.prepare_aria_s1_gunw_job(
        reference_date='ref_date_2',
        secondary_date='sec_date_2',
        frame_id=101,
        name='my_name',
    ) == {
        'job_type': 'ARIA_S1_GUNW',
        'name': 'my_name',
        'job_parameters': {
            'reference_date': 'ref_date_2',
            'secondary_date': 'sec_date_2',
            'frame_id': 101,
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
def test_submit_autorift_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('AUTORIFT', job_parameters={'granules': ['g1', 'g2']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_autorift_job('g1', 'g2')
    assert batch.jobs[0] == job


@responses.activate
def test_submit_rtc_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('RTC_GAMMA', job_parameters={'granules': ['g1']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_rtc_job('g1')
    assert batch.jobs[0] == job


@responses.activate
def test_submit_insar_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('INSAR_GAMMA', job_parameters={'granules': ['g1', 'g2']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_insar_job('g1', 'g2')
    assert batch.jobs[0] == job


@responses.activate
def test_submit_insar_isce_burst_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('INSAR_ISCE_BURST', job_parameters={'granules': ['g1', 'g2']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_insar_isce_burst_job('g1', 'g2')
    assert batch.jobs[0] == job


@responses.activate
def test_submit_insar_isce_multi_burst_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('INSAR_ISCE_MULTI_BURST', job_parameters={'reference': ['g1', 'g2'], 'secondary': ['g3', 'g4']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_insar_isce_multi_burst_job(['g1', 'g2'], ['g3', 'g4'])
    assert batch.jobs[0] == job


@responses.activate
def test_submit_aria_s1_gunw_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('ARIA_S1_GUNW', job_parameters={'reference_date': 'd1', 'secondary_date': 'd2', 'frame_id': 100})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_aria_s1_gunw_job('d1', 'd2', 100)
    assert batch.jobs[0] == job


@responses.activate
def test_submit_opera_rtc_s1_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job('OPERA_RTC_S1', job_parameters={'granules': ['g1']})
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_opera_rtc_s1_job(['g1'])
    assert batch.jobs[0] == job


@responses.activate
def test_resubmit_previous_job(get_mock_hyp3, get_mock_job):
    job = get_mock_job()
    api_response = {'jobs': [job.to_dict()]}
    api = get_mock_hyp3()
    responses.add(responses.POST, urljoin(api.url, '/jobs'), json=api_response)
    batch = api.submit_prepared_jobs(job.to_dict(for_resubmit=True))
    assert batch.jobs[0] == job


@responses.activate
def test_my_info(get_mock_hyp3):
    api_response = {'job_names': ['name1', 'name2'], 'remaining_credits': 25.0, 'user_id': 'someUser'}
    api = get_mock_hyp3()
    responses.add(responses.GET, urljoin(api.url, '/user'), json=api_response)
    response = api.my_info()
    assert response == api_response


@responses.activate
def test_check_credits(get_mock_hyp3):
    api_response = {'job_names': ['name1', 'name2'], 'remaining_credits': 25.0, 'user_id': 'someUser'}
    api = get_mock_hyp3()
    responses.add(responses.GET, urljoin(api.url, '/user'), json=api_response)

    assert math.isclose(api.check_credits(), 25.0)


@responses.activate
def test_costs(get_mock_hyp3):
    api_response = {'foo': 5}
    api = get_mock_hyp3()
    responses.add(responses.GET, urljoin(api.url, '/costs'), json=api_response)

    assert api.costs() == {'foo': 5}


@responses.activate
def test_update_jobs(get_mock_hyp3, get_mock_job):
    api = get_mock_hyp3()
    job1_api_response = {
        'job_id': 'job1',
        'job_type': 'FOO',
        'request_time': '2020-06-04T18:00:03+00:00',
        'status_code': 'SUCCEEDED',
        'user_id': 'foo',
        'name': 'new_name',
    }
    job2_api_response = {
        'job_id': 'job2',
        'job_type': 'FOO',
        'request_time': '2020-06-04T18:00:03+00:00',
        'status_code': 'SUCCEEDED',
        'user_id': 'foo',
        'name': 'new_name',
    }
    responses.add(
        responses.PATCH,
        urljoin(api.url, '/jobs/job1'),
        match=[responses.matchers.json_params_matcher({'name': 'new_name'})],
        json=job1_api_response,
    )
    responses.add(
        responses.PATCH,
        urljoin(api.url, '/jobs/job2'),
        match=[responses.matchers.json_params_matcher({'name': 'new_name'})],
        json=job2_api_response,
    )
    responses.add(
        responses.PATCH,
        urljoin(api.url, '/jobs/job1'),
        match=[responses.matchers.json_params_matcher({'foo': 'bar'})],
        json={'detail': 'test error message'},
        status=400,
    )

    job1 = get_mock_job(job_id='job1')
    job2 = get_mock_job(job_id='job2')

    assert api.update_jobs(job1, name='new_name') == Job.from_dict(job1_api_response)

    assert api.update_jobs(Batch([job1, job2]), name='new_name') == Batch(
        [Job.from_dict(job1_api_response), Job.from_dict(job2_api_response)]
    )

    with pytest.raises(TypeError):
        api.update_jobs(1, name='new_name')

    with pytest.raises(HyP3Error, match=r'^<Response \[400\]> test error message$'):
        api.update_jobs(job1, foo='bar')


def test_get_endpoint_url(get_mock_hyp3):
    api = get_mock_hyp3(api_url='https://dummy-api.asf.alaska.edu')
    assert api._get_endpoint_url('foo') == 'https://dummy-api.asf.alaska.edu/foo'
    assert api._get_endpoint_url('/foo') == 'https://dummy-api.asf.alaska.edu/foo'

    api = get_mock_hyp3(api_url='https://foo.example.com/api')
    assert api._get_endpoint_url('foo') == 'https://foo.example.com/api/foo'
    assert api._get_endpoint_url('/foo') == 'https://foo.example.com/api/foo'
    assert api._get_endpoint_url('///foo///') == 'https://foo.example.com/api/foo'

    api = get_mock_hyp3(api_url='https://foo.example.com/api/')
    assert api._get_endpoint_url('foo') == 'https://foo.example.com/api/foo'
    assert api._get_endpoint_url('/foo') == 'https://foo.example.com/api/foo'
    assert api._get_endpoint_url('///foo///') == 'https://foo.example.com/api/foo'

    api = get_mock_hyp3(api_url='https://foo.example.com:8000/api/')
    assert api._get_endpoint_url('foo') == 'https://foo.example.com:8000/api/foo'


def test_update_cookie(get_mock_hyp3):
    api = get_mock_hyp3()
    assert api.session.cookies.get('asf-urs', domain='.asf.alaska.edu') == 'test-cookie'

    api = get_mock_hyp3(api_url='https://foo.example.com:8000/api')
    assert api.session.cookies.get('asf-urs', domain='.asf.alaska.edu') == 'test-cookie'
    assert api.session.cookies.get('asf-urs', domain='foo.example.com') == 'test-cookie'

    api = get_mock_hyp3(api_url='https://foo.asf.alaska.edu:8000/api')
    assert api.session.cookies.get('asf-urs', domain='.asf.alaska.edu') == 'test-cookie'
    assert api.session.cookies.get('asf-urs', domain='foo.asf.alaska.edu') is None
