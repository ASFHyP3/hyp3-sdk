"""Errors and exceptions to raise when the SDK runs into problems"""

from requests import Response
from requests.exceptions import HTTPError


class HyP3SDKError(Exception):
    """Base Exception for the HyP3 SDK"""


class HyP3Error(HyP3SDKError):
    """Raise for errors when using the HyP3 module"""


class ASFSearchError(HyP3SDKError):
    """Raise for errors when using the ASF Search module"""


class ServerError(HyP3SDKError):
    """Raise when the HyP3 SDK encounters a server error"""


class AuthenticationError(HyP3SDKError):
    """Raise when authentication does not succeed"""


def _raise_for_hyp3_status(response: Response):
    try:
        response.raise_for_status()
    except HTTPError:
        if 400 <= response.status_code < 500:
            raise HyP3Error(f'{response} {response.json()["detail"]}')
        raise ServerError


def _raise_for_search_status(response: Response):
    try:
        response.raise_for_status()
    except HTTPError:
        if 400 <= response.status_code < 500:
            raise ASFSearchError(f'{response} {response.json()["error"]["report"]}')
        raise ServerError
