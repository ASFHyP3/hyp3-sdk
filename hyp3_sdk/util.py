"""Extra utilities for working with HyP3"""

import requests

from hyp3_sdk.exceptions import AuthenticationError

AUTH_URL = 'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g' \
           '&redirect_uri=https://auth.asf.alaska.edu/login'


def get_authenticated_session(username: str, password: str) -> requests.Session:
    """logs into hyp3 using credentials for urs.earthdata.nasa.gov from provided credentails or a .netrc file.

    Returns:
        An authenticated Session object from the requests library
    """
    s = requests.Session()
    if username and password is not None:
        if username or password is None:
            raise AuthenticationError('If either username or password are provided, both must be provided.')
        response = s.get(AUTH_URL, auth=(username, password))
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise AuthenticationError('Was not able to authenticate with .netrc file and no credentials provided')
    else:
        response = s.get(AUTH_URL)
        try:
            response.raise_for_status()
        except requests.HTTPError:
            raise AuthenticationError('Was not able to authenticate with .netrc file and no credentials provided')
    return s
