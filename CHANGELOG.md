# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) 
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added
- Methods to prepare jobs for submission to HyP3
  - `HyP3.prepare_autorift_job`
  - `HyP3.prepare_rtc_job`
  - `HyP3.prepare_insar_job`
    
### Changed
- HyP3 `Batch` objects are now iterable
- HyP3 submit methods will always return a `Batch` containing the submitted job(s)
- `HyP3.submit_job_dict` has been renamed to `HyP3.submit_prepared_jobs` and can
  submit one or more prepared job dictionaries.

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
