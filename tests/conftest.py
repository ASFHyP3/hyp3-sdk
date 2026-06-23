import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
import requests

from hyp3_sdk import Job
from hyp3_sdk.hyp3 import HyP3


@pytest.fixture(autouse=True)
def get_mock_hyp3():
    def mock_get_authenticated_session(username, password, token):
        s = requests.Session()

        if token is not None:
            s.headers.update({'Authorization': f'Bearer {token}'})
            return s

        s.cookies.set('asf-urs', 'test-cookie', domain='.asf.alaska.edu')
        return s

    def mock_hyp3(api_url: str = 'https://dummy-api.asf.alaska.edu', token: str | None = None):
        with patch('hyp3_sdk.util.get_authenticated_session', mock_get_authenticated_session):
            return HyP3(api_url=api_url, token=token)

    return mock_hyp3


@pytest.fixture(autouse=True)
def get_mock_job():
    def default_job(
        *,
        job_type: str='JOB_TYPE',
        job_id: str | None = None,
        request_time: str | datetime=datetime.now(),
        status_code: str='RUNNING',
        user_id: str='user',
        name: str | None = 'name',
        bucket: str | None = None,
        bucket_prefix: str | None = None,
        job_parameters: dict | None = None,
        files: list | None = None,
        logs: list | None = None,
        browse_images: list | None = None,
        thumbnail_images: list | None = None,
        expiration_time: datetime | None = None,
        processing_times: list[float] | None = None,
        credit_cost: float | None = None,
        priority: int | None = None,
    ):
        job_dict = locals()

        if job_dict['job_parameters'] is None:
            job_dict['job_parameters'] = {'param1': 'value1'}

        if job_dict['job_id'] is None:
            job_dict['job_id'] = str(uuid4())

        if isinstance(request_time, datetime):
            job_dict['request_time'] = request_time.isoformat(timespec='seconds')

        return Job.from_dict(job_dict)

    return default_job


@pytest.fixture
def test_data_dir():
    data_dir = Path(__file__).resolve().parent / 'data'
    return data_dir


@pytest.fixture
def product_zip(tmp_path_factory, test_data_dir):
    tmp_dir = tmp_path_factory.mktemp('data')

    product_file = tmp_dir / 'product.zip'
    shutil.copy(test_data_dir / 'product.zip', product_file)

    return product_file
