import random

import requests

AUTH_URL = 'https://urs.earthdata.nasa.gov/oauth/authorize?response_type=code&client_id=BO_n7nTIlMljdvU6kRRB3g&redirect_uri=https://auth.asf.alaska.edu/login'


def get_auth_token():
    s = requests.Session()
    s.get(AUTH_URL).content
    token = s.cookies.get_dict()['asf-urs']
    return token

