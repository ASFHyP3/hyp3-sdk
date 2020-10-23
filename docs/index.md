# HyP3 SDK

A python wrapper around the HyP3 API

## Install

The HyP3 SDK can be installed via `pip`:

```
python -m pip install hyp3_sdk
```

## Usage

The HyP3 object interactions with the HyP3 API are done using an instance of the `HyP3` class
```python
from hyp3_sdk import HyP3

api = HyP3()  # Must have credentials for urs.earthdata.nasa.gov in a .netrc file for this to work
```
If you want to use an API other then the one at `https://hyp3-api.asf.alaska.edu`, you may provide 
the URL (including scheme) as a parameter
```python
api = HyP3('https://hyp3.example.com')
```
If you want to pass in a [Requests](https://requests.readthedocs.io/en/latest/user/advanced/) `Session`
object for the API to use, it must first be authenticated and then it can be passed into the API
```python
import requests

session = requests.Session()
session.get(...)  # Authenticate

api = HyP3(authenticated_session=session)
```

The `submit_jobs` method will submit Job objects to the API for processing
```python
jobs = [make_rtc_gamma_job('job_name', 'granule_name')]

response = api.submit_jobs(jobs)
```

The `get_jobs` method will request all jobs from the API and return them in a list of dictionaries
```python
response = api.get_jobs()
```


## SDK API Reference

::: hyp3_sdk
