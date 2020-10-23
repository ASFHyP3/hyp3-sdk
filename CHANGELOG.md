# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [PEP 440](https://www.python.org/dev/peps/pep-0440/) 
and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
