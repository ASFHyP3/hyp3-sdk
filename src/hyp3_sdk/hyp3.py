import math
import time
import warnings
from datetime import datetime, timezone
from functools import singledispatchmethod
from getpass import getpass
from typing import Literal
from urllib.parse import SplitResult, urlsplit, urlunsplit
from warnings import warn

import hyp3_sdk
import hyp3_sdk.util
from hyp3_sdk.exceptions import HyP3Error, _raise_for_hyp3_status
from hyp3_sdk.jobs import Batch, Job


PROD_API = 'https://hyp3-api.asf.alaska.edu'
TEST_API = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API.

    Warning: All jobs submitted to HyP3 are publicly visible. For more information, see
    https://hyp3-docs.asf.alaska.edu/#public-visibility-of-jobs
    """

    def __init__(
        self,
        api_url: str = PROD_API,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        prompt: Literal['password', 'token'] | bool | None = None,
    ):
        """If username and password are not provided, attempts to use credentials from a `.netrc` file.

        Args:
            api_url: Address of the HyP3 API
            username: Username for authenticating to `urs.earthdata.nasa.gov`.
                Both username and password must be provided if either is provided.
            password: Password for authenticating to `urs.earthdata.nasa.gov`.
                Both username and password must be provided if either is provided.
            token: Earthdata Login Bearer Token for authenticating to `urs.earthdata.nasa.gov`
            prompt: Either 'password' or 'token' to prompt for EDL username and password or EDL bearer token, respectively.
        """
        self.url = api_url

        if prompt not in (True, False, 'password', 'token', None):
            raise ValueError(f'Unexpected value {prompt} for `prompt`')

        if prompt is True:
            warnings.warn(
                'Passing `prompt=True` is deprecated. Please use either `prompt="password"` or `prompt="token"`',
                UserWarning,
            )
            prompt = 'password'

        if prompt == 'password':
            if username is None:
                username = input('NASA Earthdata Login username: ')
            if password is None:
                password = getpass('NASA Earthdata Login password: ')

        if prompt == 'token' and token is None:
            token = getpass('NASA Earthdata Login bearer token: ')

        self.session = hyp3_sdk.util.get_authenticated_session(username, password, token)
        self.session.headers.update({'User-Agent': f'{hyp3_sdk.__name__}/{hyp3_sdk.__version__}'})

        hostname = urlsplit(self.url).hostname
        assert hostname is not None
        if not hostname.endswith('.asf.alaska.edu'):
            self.session.cookies.set('asf-urs', self.session.cookies['asf-urs'], domain=hostname)

    def _get_endpoint_url(self, endpoint: str) -> str:
        parts = urlsplit(self.url)
        path = '/'.join([parts.path.strip('/'), endpoint.strip('/')])
        return urlunsplit(SplitResult(scheme=parts.scheme, netloc=parts.netloc, path=path, query='', fragment=''))

    def find_jobs(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        status_code: str | None = None,
        name: str | None = None,
        job_type: str | None = None,
        user_id: str | None = None,
    ) -> Batch:
        """Gets a Batch of jobs from HyP3 matching the provided search criteria

        Args:
            start: only jobs submitted after given time
            end: only jobs submitted before given time
            status_code: only jobs matching this status (SUCCEEDED, FAILED, RUNNING, PENDING)
            name: only jobs with this name
            job_type: only jobs with this job_type
            user_id: only jobs submitted by this user (defaults to the current user)

        Returns:
            A Batch object containing the found jobs
        """
        params = {}
        for param_name in ('start', 'end', 'status_code', 'name', 'job_type', 'user_id'):
            param_value = locals().get(param_name)
            if param_value is not None:
                if isinstance(param_value, datetime):
                    if param_value.tzinfo is None:
                        param_value = param_value.replace(tzinfo=timezone.utc)
                    param_value = param_value.isoformat(timespec='seconds')

                params[param_name] = param_value

        response = self.session.get(self._get_endpoint_url('/jobs'), params=params)
        _raise_for_hyp3_status(response)
        jobs = [Job.from_dict(job) for job in response.json()['jobs']]

        while 'next' in response.json():
            next_url = response.json()['next']
            response = self.session.get(next_url)
            _raise_for_hyp3_status(response)
            jobs.extend([Job.from_dict(job) for job in response.json()['jobs']])

        return Batch(jobs)

    def get_job_by_id(self, job_id: str) -> Job:
        """Get job by job ID

        Args:
            job_id: A job ID

        Returns:
            A Job object
        """
        response = self.session.get(self._get_endpoint_url(f'/jobs/{job_id}'))
        _raise_for_hyp3_status(response)

        return Job.from_dict(response.json())

    @singledispatchmethod
    def watch(self, job_or_batch: Batch | Job, timeout: int = 10800, interval: int | float = 60) -> Batch | Job:
        """Watch jobs until they complete

        Args:
            job_or_batch: A Batch or Job object of jobs to watch
            timeout: How long to wait until exiting in seconds
            interval: How often to check for updates in seconds

        Returns:
            A Batch or Job object with refreshed watched jobs
        """
        raise NotImplementedError(f'Cannot watch {type(job_or_batch)} type object')

    @watch.register
    def _watch_batch(self, batch: Batch, timeout: int = 10800, interval: int | float = 60) -> Batch:
        tqdm = hyp3_sdk.util.get_tqdm_progress_bar()
        iterations_until_timeout = math.ceil(timeout / interval)
        bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{postfix[0]}]'
        with tqdm(total=len(batch), bar_format=bar_format, postfix=[f'timeout in {timeout} s']) as progress_bar:
            for ii in range(iterations_until_timeout):
                batch = self.refresh(batch)  # type: ignore [assignment]

                counts = batch._count_statuses()
                complete = counts['SUCCEEDED'] + counts['FAILED']

                progress_bar.postfix = [f'timeout in {timeout - ii * interval}s']
                # to control n/total manually; update is n += value
                progress_bar.n = complete
                progress_bar.update(0)

                if batch.complete():
                    return batch
                time.sleep(interval)
        raise HyP3Error(f'Timeout occurred while waiting for {batch}')

    @watch.register
    def _watch_job(self, job: Job, timeout: int = 10800, interval: int | float = 60) -> Job:
        tqdm = hyp3_sdk.util.get_tqdm_progress_bar()
        iterations_until_timeout = math.ceil(timeout / interval)
        bar_format = '{n_fmt}/{total_fmt} [{postfix[0]}]'
        with tqdm(total=1, bar_format=bar_format, postfix=[f'timeout in {timeout} s']) as progress_bar:
            for ii in range(iterations_until_timeout):
                job = self.refresh(job)  # type: ignore [assignment]
                progress_bar.postfix = [f'timeout in {timeout - ii * interval}s']
                progress_bar.update(int(job.complete()))

                if job.complete():
                    return job
                time.sleep(interval)
        raise HyP3Error(f'Timeout occurred while waiting for {job}')

    @singledispatchmethod
    def refresh(self, job_or_batch: Batch | Job) -> Batch | Job:
        """Refresh each jobs' information

        Args:
            job_or_batch: A Batch of Job object to refresh

        Returns:
            A Batch or Job object with refreshed information
        """
        raise NotImplementedError(f'Cannot refresh {type(job_or_batch)} type object')

    @refresh.register
    def _refresh_batch(self, batch: Batch):
        jobs = []
        for job in batch.jobs:
            jobs.append(self.refresh(job))
        return Batch(jobs)  # type: ignore [arg-type]

    @refresh.register
    def _refresh_job(self, job: Job):
        return self.get_job_by_id(job.job_id)

    def submit_prepared_jobs(self, prepared_jobs: dict | list[dict]) -> Batch:
        """Submit a prepared job dictionary, or list of prepared job dictionaries

        Args:
            prepared_jobs: A prepared job dictionary, or list of prepared job dictionaries

        Returns:
            A Batch object containing the submitted job(s)
        """
        if isinstance(prepared_jobs, dict):
            payload = {'jobs': [prepared_jobs]}
        else:
            payload = {'jobs': prepared_jobs}

        response = self.session.post(self._get_endpoint_url('/jobs'), json=payload)
        _raise_for_hyp3_status(response)

        batch = Batch()
        for job in response.json()['jobs']:
            batch += Job.from_dict(job)
        return batch

    def submit_autorift_job(self, granule1: str, granule2: str, name: str | None = None) -> Batch:
        """Submit an autoRIFT job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job

        Returns:
            A Batch object containing the autoRIFT job
        """
        job_dict = self.prepare_autorift_job(granule1, granule2, name=name)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_autorift_job(cls, granule1: str, granule2: str, name: str | None = None) -> dict:
        """Submit an autoRIFT job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job

        Returns:
            A dictionary containing the prepared autoRIFT job
        """
        job_dict = {
            'job_parameters': {'granules': [granule1, granule2]},
            'job_type': 'AUTORIFT',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_rtc_job(
        self,
        granule: str,
        name: str | None = None,
        dem_matching: bool = False,
        include_dem: bool = False,
        include_inc_map: bool = False,
        include_rgb: bool = False,
        include_scattering_area: bool = False,
        radiometry: Literal['sigma0', 'gamma0'] = 'gamma0',
        resolution: Literal[10, 20, 30] = 30,
        scale: Literal['amplitude', 'decibel', 'power'] = 'power',
        speckle_filter: bool = False,
        dem_name: Literal['copernicus'] = 'copernicus',
    ) -> Batch:
        """Submit an RTC job

        Args:
            granule: The granule (scene) to use
            name: A name for the job
            dem_matching: Coregisters SAR data to the DEM, rather than using dead reckoning based on orbit files
            include_dem: Include the DEM file in the product package
            include_inc_map: Include the local incidence angle map in the product package
            include_rgb: Include a false-color RGB decomposition in the product package for dual-pol granules
                (ignored for single-pol granules)
            include_scattering_area: Include the scattering area in the product package
            radiometry: Backscatter coefficient normalization, either by ground area (sigma0) or illuminated area
                projected into the look direction (gamma0)
            resolution: Desired output pixel spacing in meters
            scale: Scale of output image; power, decibel or amplitude
            speckle_filter: Apply an Enhanced Lee speckle filter
            dem_name: Name of the DEM to use for processing. `copernicus` is the only option, and it will use
            the Copernicus GLO-30 Public DEM.

        Returns:
            A Batch object containing the RTC job
        """
        arguments = locals()
        arguments.pop('self')
        job_dict = self.prepare_rtc_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_rtc_job(
        cls,
        granule: str,
        name: str | None = None,
        dem_matching: bool = False,
        include_dem: bool = False,
        include_inc_map: bool = False,
        include_rgb: bool = False,
        include_scattering_area: bool = False,
        radiometry: Literal['sigma0', 'gamma0'] = 'gamma0',
        resolution: Literal[10, 20, 30] = 30,
        scale: Literal['amplitude', 'decibel', 'power'] = 'power',
        speckle_filter: bool = False,
        dem_name: Literal['copernicus'] = 'copernicus',
    ) -> dict:
        """Submit an RTC job

        Args:
            granule: The granule (scene) to use
            name: A name for the job
            dem_matching: Coregisters SAR data to the DEM, rather than using dead reckoning based on orbit files
            include_dem: Include the DEM file in the product package
            include_inc_map: Include the local incidence angle map in the product package
            include_rgb: Include a false-color RGB decomposition in the product package for dual-pol granules
                (ignored for single-pol granules)
            include_scattering_area: Include the scattering area in the product package
            radiometry: Backscatter coefficient normalization, either by ground area (sigma0) or illuminated area
                projected into the look direction (gamma0)
            resolution: Desired output pixel spacing in meters
            scale: Scale of output image; power, decibel or amplitude
            speckle_filter: Apply an Enhanced Lee speckle filter
            dem_name: Name of the DEM to use for processing. `copernicus` is the only option, and it will use
            the Copernicus GLO-30 Public DEM.

        Returns:
            A dictionary containing the prepared RTC job
        """
        job_parameters = locals().copy()
        for key in ['granule', 'name', 'cls']:
            job_parameters.pop(key, None)

        job_dict = {
            'job_parameters': {'granules': [granule], **job_parameters},
            'job_type': 'RTC_GAMMA',
        }

        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_insar_job(
        self,
        granule1: str,
        granule2: str,
        name: str | None = None,
        include_look_vectors: bool = False,
        include_los_displacement: bool = False,
        include_inc_map: bool = False,
        looks: Literal['20x4', '10x2'] = '20x4',
        include_dem: bool = False,
        include_wrapped_phase: bool = False,
        apply_water_mask: bool = False,
        include_displacement_maps: bool = False,
        phase_filter_parameter: float = 0.6,
    ) -> Batch:
        """Submit an InSAR job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job
            include_look_vectors: Include the look vector theta and phi files in the product package
            include_los_displacement: Include a GeoTIFF in the product package containing displacement values
                along the Line-Of-Sight (LOS). This parameter has been deprecated in favor of
                `include_displacement_maps`, and will be removed in a future release.
            include_inc_map: Include the local and ellipsoidal incidence angle maps in the product package
            looks: Number of looks to take in range and azimuth
            include_dem: Include the digital elevation model GeoTIFF in the product package
            include_wrapped_phase: Include the wrapped phase GeoTIFF in the product package
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            include_displacement_maps: Include displacement maps (line-of-sight and vertical) in the product package
            phase_filter_parameter: Adaptive phase filter parameter.
                Useful values fall in the range 0.2 to 1.
                Larger values result in stronger filtering.
                If zero, adaptive phase filter will be skipped.

        Returns:
            A Batch object containing the InSAR job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_insar_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_insar_job(
        cls,
        granule1: str,
        granule2: str,
        name: str | None = None,
        include_look_vectors: bool = False,
        include_los_displacement: bool = False,
        include_inc_map: bool = False,
        looks: Literal['20x4', '10x2'] = '20x4',
        include_dem: bool = False,
        include_wrapped_phase: bool = False,
        apply_water_mask: bool = False,
        include_displacement_maps: bool = False,
        phase_filter_parameter: float = 0.6,
    ) -> dict:
        """Submit an InSAR job

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job
            include_look_vectors: Include the look vector theta and phi files in the product package
            include_los_displacement: Include a GeoTIFF in the product package containing displacement values
                along the Line-Of-Sight (LOS). This parameter has been deprecated in favor of
                `include_displacement_maps`, and will be removed in a future release.
            include_inc_map: Include the local and ellipsoidal incidence angle maps in the product package
            looks: Number of looks to take in range and azimuth
            include_dem: Include the digital elevation model GeoTIFF in the product package
            include_wrapped_phase: Include the wrapped phase GeoTIFF in the product package
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            include_displacement_maps: Include displacement maps (line-of-sight and vertical) in the product package
            phase_filter_parameter: Adaptive phase filter parameter.
                Useful values fall in the range 0.2 to 1.
                Larger values result in stronger filtering.
                If zero, adaptive phase filter will be skipped.

        Returns:
            A dictionary containing the prepared InSAR job
        """
        if include_los_displacement:
            warnings.warn(
                'The include_los_displacement parameter has been deprecated in favor of '
                'include_displacement_maps, and will be removed in a future release.',
                FutureWarning,
            )

        job_parameters = locals().copy()
        for key in ['cls', 'granule1', 'granule2', 'name']:
            job_parameters.pop(key)

        job_dict = {
            'job_parameters': {'granules': [granule1, granule2], **job_parameters},
            'job_type': 'INSAR_GAMMA',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_insar_isce_multi_burst_job(
        self,
        reference: list[str],
        secondary: list[str],
        name: str | None = None,
        apply_water_mask: bool = False,
        looks: Literal['20x4', '10x2', '5x1'] = '20x4',
    ) -> Batch:
        """Submit an InSAR ISCE multi burst job.

        Args:
            reference: A list of reference granules (scenes) to use
            secondary: A list of secondary granules (scenes) to use
            name: A name for the job
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            looks: Number of looks to take in range and azimuth

        Returns:
            A Batch object containing the InSAR ISCE multi burst job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_insar_isce_multi_burst_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_insar_isce_multi_burst_job(
        cls,
        reference: list[str],
        secondary: list[str],
        name: str | None = None,
        apply_water_mask: bool = False,
        looks: Literal['20x4', '10x2', '5x1'] = '20x4',
    ) -> dict:
        """Prepare an InSAR ISCE multi burst job.

        Args:
            reference: A list of reference granules (scenes) to use
            secondary: A list of secondary granules (scenes) to use
            name: A name for the job
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            looks: Number of looks to take in range and azimuth

        Returns:
            A dictionary containing the prepared InSAR ISCE multi burst job
        """
        job_parameters = locals().copy()
        for key in ['cls', 'name']:
            job_parameters.pop(key)

        job_dict = {
            'job_parameters': {**job_parameters},
            'job_type': 'INSAR_ISCE_MULTI_BURST',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_insar_isce_burst_job(
        self,
        granule1: str,
        granule2: str,
        name: str | None = None,
        apply_water_mask: bool = False,
        looks: Literal['20x4', '10x2', '5x1'] = '20x4',
    ) -> Batch:
        """Submit an InSAR ISCE burst job.

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            looks: Number of looks to take in range and azimuth

        Returns:
            A Batch object containing the InSAR ISCE burst job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_insar_isce_burst_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_insar_isce_burst_job(
        cls,
        granule1: str,
        granule2: str,
        name: str | None = None,
        apply_water_mask: bool = False,
        looks: Literal['20x4', '10x2', '5x1'] = '20x4',
    ) -> dict:
        """Prepare an InSAR ISCE burst job.

        Args:
            granule1: The first granule (scene) to use
            granule2: The second granule (scene) to use
            name: A name for the job
            apply_water_mask: Sets pixels over coastal waters and large inland waterbodies
                as invalid for phase unwrapping
            looks: Number of looks to take in range and azimuth

        Returns:
            A dictionary containing the prepared InSAR ISCE burst job
        """
        job_parameters = locals().copy()
        for key in ['cls', 'granule1', 'granule2', 'name']:
            job_parameters.pop(key)

        job_dict = {
            'job_parameters': {'granules': [granule1, granule2], **job_parameters},
            'job_type': 'INSAR_ISCE_BURST',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_aria_s1_gunw_job(
        self, reference_date: str, secondary_date: str, frame_id: int, name: str | None = None
    ) -> Batch:
        """Submit an ARIA S1 GUNW job.

        Args:
            reference_date: Date of reference scenes for InSAR processing in YYYY-MM-DD format
            secondary_date: Date of secondary scenes for InSAR processing in YYYY-MM-DD format
            frame_id: Subset GUNW products to this frame
            name: A name for the job (optional)

        Returns:
            A Batch object containing the ARIA S1 GUNW job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_aria_s1_gunw_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_aria_s1_gunw_job(
        cls, reference_date: str, secondary_date: str, frame_id: int, name: str | None = None
    ) -> dict:
        """Prepare an ARIA S1 GUNW job.

        Args:
            reference_date: Date of reference scenes for InSAR processing in YYYY-MM-DD format
            secondary_date: Date of secondary scenes for InSAR processing in YYYY-MM-DD format
            frame_id: Subset GUNW products to this frame
            name: A name for the job

        Returns:
            A dictionary containing the prepared ARIA S1 GUNW job
        """
        job_parameters = locals().copy()
        for key in ['cls', 'name']:
            job_parameters.pop(key)

        job_dict = {
            'job_parameters': job_parameters,
            'job_type': 'ARIA_S1_GUNW',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def submit_opera_rtc_s1_job(self, granule: str, name: str | None = None) -> Batch:
        """Submit an OPERA RTC-S1 job.

        Args:
            granule: The name of the S1 burst to use
            name: A name for the job (optional)

        Returns:
            A Batch object containing the OPERA RTC-S1 job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_opera_rtc_s1_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_opera_rtc_s1_job(cls, granule: str, name: str | None = None) -> dict:
        """Prepare an OPERA RTC-S1 job.

        Args:
            granule: The name of the S1 burst to use
            name: A name for the job

        Returns:
            A dictionary containing the prepared OPERA RTC-S1 job
        """
        job_parameters = locals().copy()
        for key in ['cls', 'name', 'granule']:
            job_parameters.pop(key)

        job_dict = {
            'job_parameters': {'granules': [granule], **job_parameters},
            'job_type': 'OPERA_RTC_S1',
        }
        if name is not None:
            job_dict['name'] = name
        return job_dict

    def my_info(self) -> dict:
        """Returns:
        Your user information
        """
        response = self.session.get(self._get_endpoint_url('/user'))
        _raise_for_hyp3_status(response)
        return response.json()

    def check_credits(self) -> float | int | None:
        """Returns:
        Your remaining processing credits, or None if you have no processing limit
        """
        info = self.my_info()
        return info['remaining_credits']

    def check_quota(self) -> float | int | None:
        """Deprecated method for checking your remaining processing credits; replaced by `HyP3.check_credits`

        Returns:
            Your remaining processing credits, or None if you have no processing limit
        """
        warn(
            'This method is deprecated and will be removed in a future release.\n'
            'Please use `HyP3.check_credits` instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        return self.check_credits()

    def costs(self) -> dict:
        """Returns:
        Table of job costs
        """
        response = self.session.get(self._get_endpoint_url('/costs'))
        _raise_for_hyp3_status(response)
        return response.json()

    def update_jobs(self, jobs: Batch | Job, **kwargs: object) -> Batch | Job:
        """Update the name of one or more previously-submitted jobs.

        Args:
            jobs: The job(s) to update
            kwargs:
                name: The new name, or None to remove the name

        Returns:
            The updated job(s)
        """
        if isinstance(jobs, Batch):
            batch = hyp3_sdk.Batch()
            tqdm = hyp3_sdk.util.get_tqdm_progress_bar()
            for job in tqdm(jobs):
                batch += self.update_jobs(job, **kwargs)
            return batch

        if not isinstance(jobs, Job):
            raise TypeError(f"'jobs' has type {type(jobs)}, must be {Batch} or {Job}")

        response = self.session.patch(self._get_endpoint_url(f'/jobs/{jobs.job_id}'), json=kwargs)
        _raise_for_hyp3_status(response)
        return Job.from_dict(response.json())
