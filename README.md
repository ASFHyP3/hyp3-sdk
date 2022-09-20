# HyP3 SDK

[![PyPI license](https://img.shields.io/pypi/l/hyp3_sdk.svg)](https://pypi.python.org/pypi/hyp3_sdk/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/hyp3_sdk.svg)](https://pypi.python.org/pypi/hyp3_sdk/)
[![PyPI version](https://img.shields.io/pypi/v/hyp3_sdk.svg)](https://pypi.python.org/pypi/hyp3_sdk/)
[![Conda version](https://img.shields.io/conda/vn/conda-forge/hyp3_sdk)](https://anaconda.org/conda-forge/hyp3_sdk)
[![Conda platforms](https://img.shields.io/conda/pn/conda-forge/hyp3_sdk)](https://anaconda.org/conda-forge/hyp3_sdk)

[![DOI](https://zenodo.org/badge/283858964.svg)](https://zenodo.org/badge/latestdoi/283858964)

A python wrapper around the HyP3 API

```python
>>> from hyp3_sdk import HyP3
>>> hyp3 = HyP3(username='MyUsername', password='MyPassword')

>>> granule = 'S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8'
>>> job = hyp3.submit_rtc_job(granule=granule, name='MyNewJob')
>>> job = hyp3.watch(job)
>>> job.download_files()
```

## Install

In order to easily manage dependencies, we recommend using dedicated project environments
via [Anaconda/Miniconda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) 
or [Python virtual environments](https://docs.python.org/3/tutorial/venv.html). 

The HyP3 SDK can be installed into a conda environment with

```
conda install -c conda-forge hyp3_sdk
```

or into a virtual environment with

```
python -m pip install hyp3_sdk
```

## Quick Usage

There are 3 main classes that the SDK exposes:

- `HyP3` to perform HyP3 operations (find jobs, refresh job information, submitting new jobs)
- `Job` to perform operations on single jobs (downloading products, check status)
- `Batch` to perform operations on multiple jobs at once (downloading products, check status)

An instance of the `HyP3` class will be needed to interact with the external HyP3 API.

```python
>>> from hyp3_sdk import HyP3
>>> hyp3 = HyP3(username='MyUsername', password='MyPassword')

>>> granule = 'S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8'
>>> job = hyp3.submit_rtc_job(granule=granule, name='MyNewJob')
>>> job = hyp3.watch(job)
>>> job.download_files()
```

### Submitting Jobs

`hyp3` has member functions for submitting new jobs:
```python
rtc_job = hyp3.submit_rtc_job('granule_id', 'job_name')
insar_job = hyp3.submit_insar_job('reference_granule_id', 'secondary_granule_id', 'job_name')
autorift_job = hyp3.submit_autorift_job('reference_granule_id', 'secondary_granule_id', 'job_name')
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
if not batch.complete():
    # to get updated information
    batch = hyp3.refresh(batch)
    # or to wait until completion and get updated information (which will take a fair bit)
    batch = hyp3.watch(batch)
```

Once you have complete jobs you can download the products to your machine
```python
batch.download_files()
```

These operations also work on `Job` objects
```python
job = hyp3.submit_rtc_job('S1A_IW_SLC__1SSV_20150621T120220_20150621T120232_006471_008934_72D8', 'MyJobName')
job = hyp3.watch(job)
job.download_files()
```

## Documentation

For the full SDK API Reference, see [the HyP3 documentation](https://hyp3-docs.asf.alaska.edu/using/sdk_api/)

## Contact Us

Want to talk about the HyP3 SDK? We would love to hear from you!

Found a bug? Want to request a feature?
[Open an issue](https://github.com/ASFHyP3/hyp3-sdk/issues/new)

General questions? Suggestions? Or just want to talk to the team?
[Chat with us on Gitter](https://gitter.im/ASFHyP3/community)
