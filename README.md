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

# Must either have credentials for urs.earthdata.nasa.gov in a .netrc
# or provide them in the username and password keyword args

api = HyP3()  
```

Submit a new job
```python
rtc_job = api.submit_rtc_job('MyNewJob', 'granule_id')
```

Wait for that job to complete
```python
rtc_job = api.wait(rtc_job)
```

Download files
```python
rtc_job.download_files()
```

## Documentation

For advanced usage and the SDK API Reference, see [the HyP3 documentation](https://asfhyp3.github.io/using/sdk/)

## Contact Us

Want to talk about the HyP3 SDK? We would love to hear from you!

Found a bug? Want to request a feature?
[open an issue](https://github.com/ASFHyP3/hyp3-sdk/issues/new)

General questions? Suggestions? Or just want to talk to the team?
[chat with us on gitter](https://gitter.im/ASFHyP3/community)
