import requests

AUTH_URL = 'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g' \
           '&redirect_uri=https://auth.asf.alaska.edu/login '


def get_authenticated_session():
    """logs into hyp3 using users credentials for urs.earthdata.nasa.gov in a .netrc file."""
    s = requests.Session()
    s.get(AUTH_URL)
    return s
