"""Extra utilities for working with HyP3"""

import requests

AUTH_URL = 'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g' \
           '&redirect_uri=https://auth.asf.alaska.edu/login'


def get_authenticated_session() -> requests.Session:
    """logs into hyp3 using credentials for urs.earthdata.nasa.gov from a .netrc file.

    Returns:
        An authenticated session
    """
    s = requests.Session()
    s.get(AUTH_URL)
    return s
