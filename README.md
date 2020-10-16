# HyP3 SDK

A python wrapper around the HyP3 API

## Install

The HyP3 SDK can be installed via `pip`:

```
python -m pip install hyp3_sdk
```

## Usage

### The HyP3 object
The HyP3 object interactions with the HyP3 API are done using an instance of the `HyP3` class
```python
from hyp3_sdk import HyP3

api = HyP3()  # Must have credentials for urs.earthdata.nasa.gov in a .netrc file for this to work
```
If you want to use an API other then the one at <https://hyp3-api.asf.alaska.edu>, you may provide the URL (including scheme) as a parameter
```python
from hyp3_sdk import HyP3

api = HyP3('https://hyp3.example.com')
```
If you want to pass in a [Requests](https://requests.readthedocs.io/en/latest/user/advanced/) `Session` object for the API to use, it must first be authenticated and then it can be passed into the API
```python
import requests
from hyp3_sdk import HyP3

session = requests.Session()
session.get(...)  # Authenticate

api = HyP3(authenticated_session=session)
```

#### Getting jobs
The `get_jobs` method with request all jobs from the API and return them in a list of dictionaries
```python
from hyp3_sdk import HyP3

api = HyP3()

response = api.get_jobs()
```
##### Parameters:
- `start`: `datetime` -> requests only jobs submitted after given time
- `end`: `datetime` -> requests only jobs submitted before given time
- `status`: `str` -> request based on status (`SUCCEEDED`, `FAILED`, `RUNNING`, `PENDING`)
- `name`: `str` -> requests only jobs that have this name

#### Submitting jobs
The `submit_jobs` method will submit jobs to the API for processing
```python
from hyp3_sdk import HyP3, make_rtc_gamma_job

api = HyP3()

jobs = [make_rtc_gamma_job('job_name', 'granule_name')]

response = api.submit_jobs(jobs)
```
##### Parameters
- `jobs`: `list[Job]` -> list of job objects to submit to API

### The Job object
Job objects represent a job to be submitted to the API, they are made by calling factory functions

#### Job factories
- `make_rtc_gamma_job`
  
    ##### Parameters   
    - `job_name`: `str` -> name of job
    - `granule`: `str` -> name of granule to process
    - `extra_parameters`: `dict` -> extra parameters and processing options

- `make_insar_gamma_job`
  
    ##### Parameters   
    - `job_name`: `str` -> name of job
    - `granule1`: `str` -> name of primary granule to process
    - `granule2`: `str` -> name of secondary granule to process
    - `extra_parameters`: `dict` -> extra parameters and processing options

- `make_autorift_job`

    ##### Parameters   
    - `job_name`: `str` -> name of job
    - `granule1`: `str` -> name of primary granule to process
    - `granule2`: `str` -> name of secondary granule to process
    - `extra_parameters`: `dict` -> extra parameters and processing options
