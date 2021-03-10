"""Errors and exceptions to raise when the SDK runs into problems"""

from requests import Response
from requests.exceptions import HTTPError


class HyP3Error(Exception):
    """Base Exception for the HyP3 SDK"""


class ASFSearchError(HyP3Error):
    """Raise for errors when using the ASF Search module"""


class AuthenticationError(HyP3Error):
    """Raise when authentication does not succeed"""


def hyp3_raise_for_status(response: Response):
    try:
        response.raise_for_status()
    except HTTPError:
        if 400 <= response.status_code < 500:
            raise HyP3Error(f'{response} {response.json()["detail"]}')
        raise


def search_raise_for_status(response: Response):
    try:
        response.raise_for_status()
    except HTTPError:
        if 400 <= response.status_code < 500:
            raise ASFSearchError(f'{response} {response.json()["error"]["report"]}')
        raise
