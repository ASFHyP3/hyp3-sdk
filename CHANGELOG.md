# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/)
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [7.7.1]

### Changed
* [SDK example notebook](https://github.com/ASFHyP3/hyp3-sdk/blob/main/docs/sdk_example.ipynb) now references the [HyP3 authentication notebook](https://github.com/ASFHyP3/hyp3-sdk/blob/main/docs/hyp3_authentication.ipynb) in the authentication section. 
* The [hyp3-docs authentication documentation page](https://hyp3-docs.asf.alaska.edu/using/authentication/) is linked in the [HyP3 authentication notebook](https://github.com/ASFHyP3/hyp3-sdk/blob/main/docs/hyp3_authentication.ipynb). 

## [7.7.0]

### Added
* Added support for using an [Earthdata Login Bearer Token](https://urs.earthdata.nasa.gov/documentation/for_users/user_token) when authenticating the `HyP3` object. 

## [7.6.0]
### Changed
* `ARIA-S1-GUNW` jobs now uses `reference_date` and `secondary_date` as input instead of a list of granules

## [7.5.0]

### Added
* Added support for specifying a HyP3 API URL with a non-`.asf.alaska.edu` domain name. This is accomplished by updating the domain of the `asf-urs` cookie when creating the `HyP3` object.
* Added support for specifying a HyP3 API URL that includes a path after the domain name. All API endpoints will be relative to the given path. For example, specifying `https://foo.example.com/api` results in the `/user` endpoint being relative to `/api`, i.e. `https://foo.example.com/api/user`.

## [7.4.0]

### Added
* Added `HyP3.submit_opera_rtc_s1_job` and `HyP3.prepare_opera_rtc_s1_job` methods for submitting OPERA RTC-S1 jobs to HyP3. This job type is under development and is currently only available in `https://hyp3-test-api.asf.alaska.edu`
* Added `hyp3_sdk.exceptions.ServiceUnavailableError` for handling 503 errors from HyP3.

## [7.3.0]

### Added
* Added a new `HyP3.update_jobs` method for updating the name of one or more previously-submitted jobs and an example notebook for using it.

## [7.2.1]

### Added
* Added `HyP3.submit_insar_isce_multi_burst_job` to README example

## [7.2.0]

### Added
* Added `HyP3.submit_insar_isce_multi_burst_job` and `HyP3.prepare_insar_isce_multi_burst_job` methods for submitting InSAR ISCE multi burst jobs to HyP3.

## [7.1.0]

### Added
* Added `HyP3.submit_aria_s1_gunw_job` and `HyP3.prepare_aria_s1_gunw_job` methods for submitting ARIA S1 GUNW jobs to HyP3.

## [7.0.3]

### Changed
* The [`static-analysis`](.github/workflows/static-analysis.yml) Github Actions workflow now uses `mypy` for type checking.

### Fixed
* `util.chunk` now raises `TypeError` rather than `ValueError` when given a non-integer chunk size.

## [7.0.2]

### Changed
* The [`static-analysis`](.github/workflows/static-analysis.yml) Github Actions workflow now uses `ruff` rather than `flake8` for linting.

## [7.0.1]

### Removed
* Removed the unapproved user warning implemented in [v6.2.0](https://github.com/ASFHyP3/hyp3-sdk/releases/tag/v6.2.0) (see <https://github.com/ASFHyP3/hyp3-sdk/pull/276>). This feature had unintended consequences which broke some processing pipelines that rely on the HyP3 SDK (see <https://github.com/ASFHyP3/hyp3-sdk/issues/285> for more details).

## [7.0.0]

### Removed
* Support for Python 3.9 has been removed.

## [6.2.0]

### Added
* `Job.priority` attribute
* Unapproved `hyp3-sdk` users receive an error message when connecting to `HyP3`

## [6.1.0]

### Added
* `HyP3.costs` method to retrieve the job cost lookup table, following the addition of the `/costs` API endpoint in HyP3 v6.2.0
* `Batch.total_credit_cost` method to calculate the total credit cost for a batch of jobs

## [6.0.0]
This release accommodates changes to the HyP3 API schema introduced in HyP3 v6.0.0

### Added
* `credit_cost` attribute to the `Job` class
* `HyP3.check_credits` method to determine your remaining processing credits

### Changed
* `HyP3.my_info()`: A new `remaining_credits` field replaces the `quota` field in the return value
* `HyP3.check_quota` may return a float or an integer if the user has processing credits

### Deprecated
* `HyP3.check_quota` has been deprecated in favor of `HyP3.check_credits`

## [5.0.0]
### Removed
* `legacy` option for the `dem_name` argument of `HyP3.prepare_rtc_job()` and `HyP3.submit_rtc_job()`.

## [4.0.0]
### Added
* The HyP3 SDK now explicitly supports Python 3.9-3.12
* Added `HyP3.submit_insar_isce_burst_job` and `HyP3.prepare_insar_isce_burst_job` methods for submitting
  InSAR ISCE burst jobs to HyP3.
* A `pending` method to the `Job` class.
* A `pending` argument to the `Batch.filter_jobs()` method.

### Changed
* The order of the arguments for `Batch.filter_jobs()`. The new order is `succeeded, pending, running, failed, include_expired`.

### Removed
* Support for Python 3.8 has been dropped.

### Fixed
* The `running` method of the `Job` class now only returns `True` if job has status `RUNNING`. Jobs in the `PENDING` state now return `True` when calling the `pending` method of `Job`.

## [3.1.0]
### Added
* Added the `phase_filter_parameter` keyword argument for the `HyP3.submit_insar_job` and `HyP3.prepare_insar_job` methods.

## [3.0.0]
### Removed
* Removed the `Job.subscription_id` attribute in response to the Subscriptions feature being removed from HyP3.

## [2.1.1]
### Fixed
* The `user_id` parameter has been moved to the end of the `HyP3.find_jobs` parameter list, to avoid
  introducing breaking changes for users who rely on the order of the parameters.

## [2.1.0]
### Added
* The `HyP3.find_jobs` method now includes a `user_id` parameter that allows retrieving jobs for a given user.
  If not provided, jobs are retrieved for the current user.

## [2.0.2]
### Added
* 20 m can now be provided to the `resolution` keyword argument of `hyp3.submit_rtc_job` and `hyp3.prepare_rtc_job`.

## [2.0.1]
### Fixed
* Display the improved error messages regardless of whether the Earthdata credentials were provided by a `.netrc` file.

## [2.0.0]
### Changed
* Improved error messages when Earthdata user must select Study Area or accept EULA, thanks to @kevinxmorales in #170
### Removed
* The `hyp3_sdk.TESTING` constant has been removed in favor of mocking objects in unit tests.

## [1.7.5]
### Fixed
* Path to `README.md` in `pyproject.toml` so that there is a package description on PyPI

## [1.7.4]
### Changed
* `hyp3-sdk` now uses a `src` layout per this [recommendation](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).
* `hyp3-sdk` now only uses `pyproject.toml` for package creation now that `setuptools` recommends [not using setup.py](https://setuptools.pypa.io/en/latest/userguide/quickstart.html#setuppy-discouraged).
* `hyp3_sdk.util` is now included in the main `hyp3_sdk` API and does not need to be imported separately

## [1.7.3]
### Added
* 10 m can now be provided to the `resolution` keyword argument of `hyp3.submit_rtc_job` and `hyp3.prepare_rtc_job`.

## [1.7.2]
### Added
* In addition to `power` and `amplitude`, `decibel` can now be provided to the `scale` keyword argument of `hyp3.submit_rtc_job` and `hyp3.prepare_rtc_job`.

## [1.7.1]
### Changed
* Updated SDK example notebook to only use the ESA S2 naming convention for autoRIFT jobs.

## [1.7.0]
### Added
- Added a `processing_times` attribute to the `hyp3_sdk.Job` class to support jobs with multiple processing steps.
### Removed
- Removed the `processing_time_in_seconds` attribute from the `hyp3_sdk.Job` class.

## [1.6.1]
### Added
- `Job` now has a `subscription_id` attribute.

## [1.6.0]
### Changed
- `Job.expired()` now returns `False` if `expiration_time` is `None`.

## [1.5.1]
### Changed
- Updated return type for `HyP3.check_quota()` to reflect the case where a user has no quota.

## [1.5.0]
### Added
- Added `processing_time_in_seconds` to `Job` class.
### Removed
- `hyp3_sdk.asf_search` has been removed and its functionality has been superseded by the
  [`asf_search`](https://github.com/asfadmin/Discovery-asf_search) Python package, which provides a more comprehensive
  ASF search experience and is available on conda-forge and PyPI.

## [1.4.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.4.1...v1.4.1)

### Fixed
- Slicing a `Batch` object will now return a new `Batch` instead of `list` of jobs
- `Batch` equality now compares the contained jobs and not object identity

## [1.4.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.3.2...v1.4.0)

### Added
- Exposed new `include_displacement_maps` parameter for `HyP3.prepare_insar_job` and `HyP3.submit_insar_job`, which will
  cause both a line-of-sight displacement and a vertical displacement GeoTIFF to be included in the product.

### Deprecated
- The `include_los_displacement` parameter of `HyP3.prepare_insar_job` and `HyP3.submit_insar_job` has been
  deprecated in favor of the `include_displacement_maps` parameter, and will be removed in the future.
- `hyp3_sdk.asf_search` is deprecated and will be removed in future releases.
  Functionality has been superseded by the [`asf_search`](https://github.com/asfadmin/Discovery-asf_search)
  Python package, which provides a more comprehensive ASF search experience and is available on conda-forge and PyPI.
  - instead of `hyp3_sdk.asf_search.get_metadata`, try `asf_search.granule_search` or `asf_search.product_search`
  - instead of `hyp3_sdk.asf_search.get_nearest_neighbors`, try `asf_search.baseline_search.stack_from_product` or `asf_search.baseline_search.stack_from_id`

## [1.3.2](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.3.1...v1.3.2)

### Added
- Exposed new `apply_water_mask` parameter for InSAR jobs in `HyP3.submit_insar_job()` and
  `HyP3.prepare_insar_job()`, which sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping

## [1.3.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.3.0...v1.3.1)

### Fixed
- Resolved an issue where `HyP3.find_jobs()` did not correctly filter results when using the `status_code` parameter

## [1.3.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.2.0...v1.3.0)

### Added
- `extract_zipped_product` function to `hyp3_sdk.util` which will extract zipped HyP3 products
- `chunk` function to `hyp3_sdk.util` which will split a sequence into small chunks and
  is particularly useful for submitting large batches

### Changed
- HyP3 API URL constants have been renamed to be more descriptive
  - `hyp3_sdk.HyP3_PROD` is now `hyp3_sdk.PROD_API`
  - `hyp3_sdk.HyP3_TEST` is now `hyp3_sdk.TEST_API`

## [1.2.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.1.3...v1.2.0)

### Added
- `Job` class now has a `logs` attribute containing links to job log files
- Added missing [container methods](https://docs.python.org/3/reference/datamodel.html#emulating-container-types)
  - batches are now subscriptable: `batch[0]`
  - jobs can be searched for in batches:`job in batch`
  - jobs can be deleted from batches: `del batch[0]`
  - batches can be reversed now using the `reversed()` function
- `find_jobs()` now accepts datetimes with no timezone info and defaults to UTC.

### Removed
- `FoundZeroJobs` warning from `find_jobs()`

### Fixed
- [#92](https://github.com/ASFHyP3/hyp3-sdk/issues/92) -- `ImportError` being
  raised when showing a progress bar because `ipywidgets` may not always be
  installed when running in a Jupyter kernel

## [1.1.3](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.1.2...v1.1.3)

### Added
- Exposed new `include_wrapped_phase` parameter for InSAR jobs in `HyP3.submit_insar_job()` and
  `HyP3.prepare_insar_job()`

## [1.1.2](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.1.1...v1.1.2)

### Added
- Exposed new `include_dem` parameter for InSAR jobs in `HyP3.submit_insar_job()` and `HyP3.prepare_insar_job()`

## [1.1.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.1.0...v1.1.1)

### Added
- Exposed new `include_inc_map` parameter for InSAR jobs in `HyP3.submit_insar_job()` and `HyP3.prepare_insar_job()`

## [1.1.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v1.0.0...v1.1.0)

### Added
- A `dem_name` parameter has been added to `HyP3.submit_rtc_job` and `HyP3.prepare_rtc_job` to control which DEM data
  set is used for RTC processing
  - `dem_name='copernicus'` will use the [Copernicus GLO-30 Public DEM](https://registry.opendata.aws/copernicus-dem/)
  - `dem_name='legacy'` will use the DEM with the best coverage from ASF's legacy SRTM/NED data sets

## [1.0.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.6.0...v1.0.0)

### Added
- `HyP3.find_jobs` now supports filtering by `job_type`
- `HyP3.find_jobs` now pages through truncated responses to get all requested jobs
- `hyp3_sdk.exceptions` now includes `ServerError` for exceptions that are a result of
  system errors.

### Changed
- `hyp3_sdk.exceptions` now has `HyP3SDKError` as a module base exception, and `HyP3Error` is now specific
  errors in the `hyp3` submodule
- `HyP3.find_jobs` argument `status` renamed to `status_code` to be consistent with api-spec

## [0.6.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.5.0...v0.6.0)

### Added
- `asf_search` module will now raise an `exceptions.ASFSearchError` when it encounters problems and
  will include the Search API response details
- `HyP3.__init__` now accepts a `prompt=True` (default `False`) keyword argument
  which will prompt users for their username or password if not provided

### Changed
- HyP3 prepare and submit methods now include processing options as named parameters
- Exceptions raised for HyP3 errors will include the HyP3 API response details
- `asf_search.get_nearest_neighbors` is no longer dependent on state vector information in CMR
  - now limited to Sentinel-1 granules
  - now raises `ASFSearchError` when the reference granule cannot be found
  - results no longer include `perpendicularBaseline` or `temporalBaseline` fields

### Fixed
- `get_authenticated_session` now correctly throws `AuthenticationError` when no `.netrc` file
  exists and no credentials are provided


## [0.5.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.4.0...v0.5.0)

### Added
- Methods to prepare jobs for submission to HyP3
  - `HyP3.prepare_autorift_job`
  - `HyP3.prepare_rtc_job`
  - `HyP3.prepare_insar_job`
- `HyP3.watch`, `Job.download_files`, and `Batch.download_files` now display progress bars

### Changed
- HyP3 `Job` objects provide a better string representation
  ```python
  >>> print(job)
  HyP3 RTC_GAMMA job dd884703-cdbf-47ff-848c-de1e2b9917c1
  ```

- HyP3 `Batch` objects
  - are now iterable
  - provide a better string representation
    ```python
    >>> print(batch)
    2 HyP3 Jobs: 0 succeeded, 0 failed, 2 running, 0 pending.
    ```

- HyP3 submit methods will always return a `Batch` containing the submitted job(s)
- `HyP3.submit_job_dict` has been renamed to `HyP3.submit_prepared_jobs` and can
  submit one or more prepared job dictionaries.
- `Job.download_files` and `Batch.download_files` will (optionally) create the
  download location if it doesn't exist
- `Hyp3._get_job_by_id` has been made public and renamed to `Hyp3.get_job_by_id`

## [0.4.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.3.3...v0.4.0)

### Added
- `hyp3_sdk.asf_search` module to find granule(s) metadata, and a granule's nearest neighbors for InSAR

##  [0.3.3](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.3.2...v0.3.3)

### Added
- SDK will attach a `User-Agent` statement like `hyp3_sdk/VERSION` to all API interactions

### Changed
- Providing a job list to `Batch.__init__()` is now optional; an empty batch will
  be created if the job list is not provided
- `Batch.__init__()` no longer issues a warning when creating an empty batch
- `HyP3.find_jobs()` will now issue a warning when a zero jobs were found

## [0.3.2](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.3.1...v0.3.2)

### Changed
- `Job.download_files` and `Batch.download_files` now default to downloading to working directory

### Fixed
- Corrected syntax errors in documentation examples

## [0.3.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.3.0...v0.3.1)

### Changed
- Correctly specifies the minimum python version (3.8) in `setup.py`
- Job.download_files and `Batch.download_files` now except strings for location in addition to `pathlib.Path`
- Updated documentation to represent version 0.3.0

## [0.3.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.2.1...v0.2.2)

### Changed
- This is a complete refactor of the API, please view updated documentation.
- API responses now return Batch objects if multiple jobs present.
- Job and Batch objects now have the following member functions to help with common tasks
- API can now watch Jobs or Batches for completion
- Jobs are no longer created then submitted, instead submission through the API is how to get Jobs
- hyp3-sdk has dropped support for python <= 3.7

## [0.2.2](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.2.1...v0.2.2)

### Added
- typehints and docstrings throughout the SDK for auto-documentation of the API

### Changed
- Documentation now is mainly contained in [The HyP3 Docs](https://asfhyp3.github.io/)
  and the README just contains quick installation and usage information

## [0.2.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.2.0...v0.2.1)

### Changed
- Updated the documentation with mostly minor style and language changes

## [0.2.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.1.1...v0.2.0)

### Added
- `hyp3.get_jobs` now accepts a `name` parameter to search by job name

## [0.1.1](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.1.0...v0.1.1)

### Fixed
- Removed space from auth URL that prevents successful sign in

## [0.1.0](https://github.com/ASFHyP3/hyp3-sdk/compare/v0.0.0...v0.1.0)

### Added
- HyP3 module
  - HyP3 class which wraps a hyp3 API
  - Job class used to define Jobs to submit and are created with the `make_[job_type]_job()`
     factory functions
