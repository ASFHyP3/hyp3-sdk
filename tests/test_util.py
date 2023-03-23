import shutil
from pathlib import Path

import pytest
import requests
import responses

from hyp3_sdk import util
from hyp3_sdk.exceptions import AuthenticationError


@responses.activate
def test_get_authenticated_session():
    responses.add(responses.GET, util.AUTH_URL, status=200)
    assert isinstance(util.get_authenticated_session('user', 'pass'), requests.Session)
    assert isinstance(util.get_authenticated_session(None, None), requests.Session)


@responses.activate
def test_get_authenticated_session_eula():
    redirect_url = (
        'https://auth.asf.alaska.edu/login?error=access_denied&error_msg=Pre%20authorization%20required%20for'
        '%20this%20application,%20please%20authorize%20by%20visiting%20the%20resolution%20url'
        '&resolution_url=https://urs.earthdata.nasa.gov/approve_app?client_id=foo'
    )
    responses.add(responses.GET, util.AUTH_URL, status=302, headers={'Location': redirect_url})
    responses.add(responses.GET, redirect_url, status=401)

    match = (
        r'^Pre authorization required for this application, please authorize by visiting '
        r'the resolution url: https://urs\.earthdata\.nasa\.gov/approve_app\?client_id=foo$'
    )
    with pytest.raises(AuthenticationError, match=match):
        util.get_authenticated_session('user', 'pass')

    with pytest.raises(AuthenticationError, match=match):
        util.get_authenticated_session(None, None)


@responses.activate
def test_get_authenticated_session_study_area():
    redirect_url = (
        'https://auth.asf.alaska.edu/login?error=access_denied&error_msg=Please%20update%20your%20profile%20for'
        '%20application%20required%20attributes%20Study%20Area'
    )
    responses.add(responses.GET, util.AUTH_URL, status=302, headers={'Location': redirect_url})
    responses.add(responses.GET, redirect_url, status=401)

    match = (
        r'^Please update your profile for application required attributes Study Area: '
        r'https://urs\.earthdata\.nasa\.gov/profile$'
    )
    with pytest.raises(AuthenticationError, match=match):
        util.get_authenticated_session('user', 'pass')

    with pytest.raises(AuthenticationError, match=match):
        util.get_authenticated_session(None, None)


@responses.activate
def test_get_authenticated_session_http_error():
    responses.add(responses.GET, util.AUTH_URL, status=401)

    with pytest.raises(
        AuthenticationError,
        match=r'^Was not able to authenticate with credentials provided.*'
    ):
        util.get_authenticated_session('user', 'pass')

    with pytest.raises(
        AuthenticationError,
        match=r'^Was not able to authenticate with \.netrc file and no credentials provided.*'
    ):
        util.get_authenticated_session(None, None)


@responses.activate
def test_download_file(tmp_path):
    responses.add(responses.GET, 'https://foo.com/file', body='foobar')
    result_path = util.download_file('https://foo.com/file', tmp_path / 'file')
    assert result_path == (tmp_path / 'file')
    assert result_path.read_text() == 'foobar'


@responses.activate
def test_download_file_string_format(tmp_path):
    responses.add(responses.GET, 'https://foo.com/file2', body='foobar2')
    result_path = util.download_file('https://foo.com/file2', str(tmp_path / 'file2'))
    assert result_path == (tmp_path / 'file2')
    assert result_path.read_text() == 'foobar2'
    assert isinstance(result_path, Path)


@responses.activate
def test_download_file_chunked_response(tmp_path):
    responses.add(responses.GET, 'https://foo.com/file3', body='foobar3')
    result_path = util.download_file('https://foo.com/file3', tmp_path / 'file3', chunk_size=3)
    assert result_path == (tmp_path / 'file3')
    assert result_path.read_text() == 'foobar3'


def test_chunk():
    items = list(range(1234))
    chunks = list(util.chunk(items))
    assert len(chunks) == 7
    assert len(chunks[0]) == 200
    assert len(chunks[-1]) == 34

    chunks = list(util.chunk(items, n=56))
    assert len(chunks) == 23
    assert len(chunks[0]) == 56
    assert len(chunks[-1]) == 2

    chunks = list(util.chunk(items, n=1234))
    assert len(chunks) == 1
    assert len(chunks[0]) == 1234

    chunks = list(util.chunk(items, n=5678))
    assert len(chunks) == 1
    assert len(chunks[0]) == 1234

    with pytest.raises(ValueError):
        chunks = list(util.chunk(items, n=0))

    with pytest.raises(ValueError):
        chunks = list(util.chunk(items, n=-2))

    with pytest.raises(ValueError):
        chunks = list(util.chunk(items, n=10.0))


def test_extract_zipped_product(product_zip):
    extracted = util.extract_zipped_product(product_zip, delete=False)
    assert extracted.exists()
    assert product_zip.exists()

    for file_name in ('foobar.txt', 'fizzbuzz.txt'):
        product_file = extracted / file_name
        assert product_file.exists()
        assert product_file.read_text().strip() == product_file.stem

    shutil.rmtree(extracted)
    extracted = util.extract_zipped_product(product_zip, delete=True)
    assert extracted.exists()
    assert not product_zip.exists()
