from datetime import datetime, timedelta
from urllib.parse import urljoin
import json

import responses

import hyp3_sdk
from hyp3_sdk import HyP3, Job
from tests.helpers import get_mock_job

hyp3_sdk.TESTING = True


@responses.activate
def test_find_jobs():
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
    responses.add(responses.GET, urljoin(api.url, '/jobs'), body=json.dumps(api_response_mock))
    response = api.find_jobs()
    assert len(response) == 3

def test_get_job_by_id():

    assert False


def test_watch():
    assert False


def test_refresh():
    assert False


def test_submit_raw_job():
    assert False


def test_submit_autorift_job():
    assert False


def test_submit_rtc_job():
    assert False


def test_submit_insar_job():
    assert False


def test_my_info():
    assert False


def test_check_quota():
    assert False
