"""Extra utilities for working with HyP3"""
from pathlib import Path
from typing import Union

import requests
from requests.adapters import HTTPAdapter
from tqdm.auto import tqdm
from urllib3.util.retry import Retry

import hyp3_sdk
from hyp3_sdk.exceptions import AuthenticationError

AUTH_URL = 'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g' \
           '&redirect_uri=https://auth.asf.alaska.edu/login&app_type=401'


def get_authenticated_session(username: str, password: str) -> requests.Session:
    """Log into HyP3 using credentials for `urs.earthdata.nasa.gov` from either the provided
     credentials or a `.netrc` file.

    Returns:
        An authenticated HyP3 Session
    """
    s = requests.Session()
    if hyp3_sdk.TESTING:
        return s
    if username is not None and password is not None:
        response = s.get(AUTH_URL, auth=(username, password))
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise AuthenticationError('Was not able to authenticate with credentials provided\n'
                                      'This could be due to invalid credentials or a connection error.')
    else:
        response = s.get(AUTH_URL)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise AuthenticationError('Was not able to authenticate with .netrc file and no credentials provided\n'
                                      'This could be due to invalid credentials in .netrc or a connection error.')
    return s


def download_file(url: str, filepath: Union[Path, str], chunk_size=None, retries=2, backoff_factor=1) -> Path:
    """Download a file
    Args:
        url: URL of the file to download
        filepath: Location to place file into
        chunk_size: Size to chunk the download into
        retries: Number of retries to attempt
        backoff_factor: Factor for calculating time between retries
    Returns:
        download_path: The path to the downloaded file
    """
    filepath = Path(filepath)
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    session.mount('https://', HTTPAdapter(max_retries=retry_strategy))
    session.mount('http://', HTTPAdapter(max_retries=retry_strategy))

    with session.get(url, stream=True) as s:
        s.raise_for_status()
        with tqdm.wrapattr(open(filepath, "wb"), 'write', miniters=1, desc=filepath.name,
                           total=int(s.headers.get('content-length', 0))) as f:
            for chunk in s.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    session.close()

    return filepath
