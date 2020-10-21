# HyP3 SDK

A python wrapper around the HyP3 API

## Install

The HyP3 SDK can be installed via `pip`:

```
python -m pip install hyp3_sdk
```

## Quick Usage

The HyP3 object interactions with the HyP3 API are done using an instance of the `HyP3` class
```python
from hyp3_sdk import HyP3

api = HyP3()  # Must have credentials for urs.earthdata.nasa.gov in a .netrc file for this to work
```
The `get_jobs` method with request all jobs from the API and return them in a list of dictionaries
```python
response = api.get_jobs()
```

The `submit_jobs` method will submit jobs to the API for processing
```python
from hyp3_sdk import make_rtc_gamma_job

jobs = [make_rtc_gamma_job('job_name', 'granule_name')]

response = api.submit_jobs(jobs)
```

## Documentation

For advanced usage and the SDK API Reference, see [the HyP3 documentation](https://asfhyp3.github.io/)

## Contact Us

Want to talk about the HyP3 SDK? We would love to hear from you!

Found a bug? Want to request a feature?
[open an issue](https://github.com/ASFHyP3/hyp3-sdk/issues/new)

General questions? Suggestions? Or just want to talk to the team?
[chat with us on gitter](https://gitter.im/ASFHyP3/community)
