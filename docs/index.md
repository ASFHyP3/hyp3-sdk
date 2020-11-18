# HyP3 SDK

A python wrapper around the HyP3 API
```python
>>> from hyp3_sdk import HyP3
>>> hyp3 = HyP3(username='MyUsername', password='MyPassword')  
>>> job = hyp3.submit_rtc_job(name='MyNewJob', granule='S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8')
>>> job = hyp3.wait(job)
>>> job.download_files()
```

## Install

The HyP3 SDK can be installed via `pip`:

```
python -m pip install hyp3_sdk
```

## Quickstart

There are 3 main classes that the SDK exposes:

- `HyP3`: to perform HyP3 operations (find jobs, refresh job information, submitting new jobs)
- `Job`: to perform operations on single jobs (downloading products, check status)
- `Batch`: to perform operations on multiple jobs at once (downloading products, check status)

An instance of the `HyP3` class will be needed to interact with the external HyP3 API.
```python
from hyp3_sdk import HyP3

# Must either have credentials for urs.earthdata.nasa.gov in a .netrc
hyp3 = HyP3()
# or provide them in the username and password keyword args
hyp3 = HyP3(username='MyUsername', password='MyPassword')
```

### Submitting Jobs

`hyp3` has member functions for submitting new jobs:
```python
rtc_job = hyp3.submit_rtc_job('job_name', 'granule_id')
insar_job = hyp3.submit_insar_job('job_name', 'reference_granule_id', 'secondary_granule_id')
autorift_job = hyp3.submit_autorift_job('job_name', 'reference_granule_id', 'secondary_granule_id')
```
Each of these functions will return an instance of the `Job` class that represents a new HyP3 job request.

### Finding Existing Jobs
To find HyP3 jobs that were run previously, you can use the `hyp3.find_jobs()`
```python
batch = hyp3.find_jobs()
```
This will return a `Batch` instance representing all jobs owned by you. You can also pass parameters to 
query to a specific set of jobs


### Operations on Job and Batch

If your jobs are not complete you can use the HyP3 instance to update them, and wait from completion
```python
batch = hyp3.find_jobs()
if not job_or_batch.complete():
    # to get updated information
    batch = hyp3.refresh(batch)
    # or to wait until completion and get updated information (which will take a fair bit)
    batch = hyp3.wait(batch) 
```

Once you have complete jobs you can download the products to your machine
```python
batch.download_files()
```

These operations also work on `Job` objects
```python
job = hyp3.submit_rtc_job('MyJobName', 'S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8')
job = hyp3.wait(job)
job.download_files()
```

## SDK API Reference

::: hyp3_sdk
