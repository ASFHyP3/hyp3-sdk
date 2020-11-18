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
>>> from hyp3_sdk import HyP3
>>> hyp3 = HyP3(username='MyUsername', password='MyPassword')  
>>> job = hyp3.submit_rtc_job(name='MyNewJob', granule='S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8')
>>> job = hyp3.wait(job)
>>> job.download_files()
```
## Documentation

For advanced usage and the SDK API Reference, see [the HyP3 documentation](https://hyp3-docs.asf.alaska.edu/using/sdk/)

## Contact Us

Want to talk about the HyP3 SDK? We would love to hear from you!

Found a bug? Want to request a feature?
[open an issue](https://github.com/ASFHyP3/hyp3-sdk/issues/new)

General questions? Suggestions? Or just want to talk to the team?
[chat with us on gitter](https://gitter.im/ASFHyP3/community)
