"""Extra utilities for working with HyP3"""

import urllib.parse
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from hyp3_sdk.exceptions import AuthenticationError


AUTH_URL = (
    'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g'
    '&redirect_uri=https://auth.asf.alaska.edu/login&app_type=401'
)

PROFILE_URL = 'https://urs.earthdata.nasa.gov/profile'


def extract_zipped_product(zip_file: str | Path, delete: bool = True) -> Path:
    """Extract a zipped HyP3 product

    Extract a zipped HyP3 product to the same directory as the zipped HyP3 product, optionally
    deleting `zip file` afterward.

    Args:
        zip_file: Zipped HyP3 product to extract
        delete: Delete `zip_file` after it has been extracted

    Returns:
        Path to the HyP3 product folder containing the product files
    """
    zip_file = Path(zip_file)
    with ZipFile(zip_file) as z:
        z.extractall(path=zip_file.parent)

    if delete:
        zip_file.unlink()

    return zip_file.parent / zip_file.stem


def chunk(itr: Sequence[Any], n: int = 200) -> Generator[Sequence[Any], None, None]:
    """Split a sequence into small chunks

    Args:
        itr: A sequence object to chunk
        n: Size of the chunks to return
    """
    error_message = f'n must be a positive integer: {n}'
    if not isinstance(n, int):
        raise TypeError(error_message)
    if n < 1:
        raise ValueError(error_message)

    for i in range(0, len(itr), n):
        yield itr[i : i + n]


def get_tqdm_progress_bar():
    try:
        # https://github.com/ASFHyP3/hyp3-sdk/issues/92
        import ipywidgets  # noqa: F401
        from tqdm.auto import tqdm
    except ImportError:
        from tqdm.std import tqdm  # type: ignore[assignment]
    return tqdm


def get_authenticated_session(
    username: str | None = None, password: str | None = None, token: str | None = None
) -> requests.Session:
    """Log into HyP3 using credentials for `urs.earthdata.nasa.gov` from either the provided
     credentials or a `.netrc` file.

    Returns:
        An authenticated HyP3 Session
    """
    s = requests.Session()

    if token is not None:
        s.headers.update({'Authorization': f'Bearer {token}'})
        return s

    if username is not None and password is not None:
        response = s.get(AUTH_URL, auth=(username, password))
        auth_error_message = (
            'Was not able to authenticate with username and password provided\n'
            'This could be due to invalid credentials or a connection error.'
        )
    else:
        response = s.get(AUTH_URL)
        auth_error_message = (
            'Was not able to authenticate with .netrc file and no credentials provided\n'
            'This could be due to invalid credentials in .netrc or a connection error.'
        )

    parsed_url = urllib.parse.urlparse(response.url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    error_msg = query_params.get('error_msg')
    resolution_url = query_params.get('resolution_url')

    if error_msg is not None and resolution_url is not None:
        raise AuthenticationError(f'{error_msg[0]}: {resolution_url[0]}')

    if error_msg is not None and 'Please update your profile' in error_msg[0]:
        raise AuthenticationError(f'{error_msg[0]}: {PROFILE_URL}')

    try:
        response.raise_for_status()
    except requests.HTTPError:
        raise AuthenticationError(auth_error_message)

    return s


def download_file(url: str, filepath: Path | str, chunk_size=None, retries=2, backoff_factor=1) -> Path:
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
    stream = False if chunk_size is None else True
    with session.get(url, stream=stream) as s:
        s.raise_for_status()
        tqdm = get_tqdm_progress_bar()
        with tqdm.wrapattr(
            open(filepath, 'wb'), 'write', miniters=1, desc=filepath.name, total=int(s.headers.get('content-length', 0))
        ) as f:
            for chunk in s.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
    session.close()

    return filepath
