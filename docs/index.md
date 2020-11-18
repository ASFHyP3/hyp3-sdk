# HyP3 SDK

A python wrapper around the HyP3 API

## Install

The HyP3 SDK can be installed via `pip`:

```
python -m pip install hyp3_sdk
```

## Usage

There are 3 main classes that the sdk exposes for you to use:

- HyP3: which is used to perfrom api operations (getting jobs, refreshing information, submitting new requests)
- Job: which is used to perform operations on single jobs (download, check status)
- Batch: which is used to perfrom operations on multiple jobs at once (download, check status)

An instance of the `HyP3` class will be needed to interact with the external HyP3 API.
```python
from hyp3_sdk import HyP3

# Must either have credentials for urs.earthdata.nasa.gov in a .netrc
# or provide them in the username and password keyword args
hyp3 = HyP3()
```
If you want to use an API other then the one at `https://hyp3-api.asf.alaska.edu`, you may provide 
the URL (including scheme) as a parameter
```python
hyp3 = HyP3('https://hyp3.example.com')
```

## Submitting Jobs

The instance of HyP3 has member functions for submitting new jobs:
- `job = submit_rtc_job('job_name', 'granule_id')` 
- `job = submit_insar_job('job_name', 'reference_granule_id', 'secondary_granule_id')` 
- `job = submit_rtc_job('job_name', 'reference_granule_id', 'secondary_granule_id')` 
Each of these functions will return an instance of the Job class that represents a new HyP3 job request.

## Finding existing Jobs
To find HyP3 Jobs that were run previously, you can use the `find_jobs()` member
of a HyP3 instance.
```python
hyp3 = HyP3()

batch = hyp3.find_jobs()
```
By default, this will return a Batch instance representing all jobs owned by your user.


## Operations on Job and batch

If your jobs are not complete you can use the HyP3 instance to update them, and wait from completion
```python
job_or_batch = hyp3.find_jobs()
job_or_batch = hyp3.refresh(job_or_batch) # gets new information and overwrites the existing Job/batch with it

job_or_batch = hyp3.watch(job_or_batch) # will run until job is complete this will take quite some time
```

Once you have complete jobs you can download the products to your machine
```python
job_or_batch = hyp3.find_jobs()
hyp3.wait(job_or_batch)

job_or_batch.download_files()
```

You can also use the HyP3 instance to refresh and wait for batches of jobs.

## SDK API Reference

::: hyp3_sdk
