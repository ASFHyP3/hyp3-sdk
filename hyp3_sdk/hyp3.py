import math
import time
import warnings
from datetime import datetime, timezone
from functools import singledispatchmethod
from getpass import getpass
from typing import List, Literal, Optional, Union
from urllib.parse import urljoin

import hyp3_sdk
from hyp3_sdk.exceptions import HyP3Error, _raise_for_hyp3_status
from hyp3_sdk.jobs import Batch, Job
from hyp3_sdk.util import get_authenticated_session, get_tqdm_progress_bar

PROD_API = 'https://hyp3-api.asf.alaska.edu'
TEST_API = 'https://hyp3-test-api.asf.alaska.edu'


class HyP3:
    """A python wrapper around the HyP3 API"""

    def __init__(self, api_url: str = PROD_API, username: Optional[str] = None, password: Optional[str] = None,
                 prompt: bool = False):
        """
        Args:
            api_url: Address of the HyP3 API
            username: Username for authenticating to `urs.earthdata.nasa.gov`.
                Both username and password must be provided if either is provided.
            password: Password for authenticating to `urs.earthdata.nasa.gov`.
                Both username and password must be provided if either is provided.
            prompt: Prompt for username and/or password interactively when they
                are not provided as keyword parameters
        """
        self.url = api_url

        if username is None and prompt:
            username = input('NASA Earthdata Login username: ')
        if password is None and prompt:
            password = getpass('NASA Earthdata Login password: ')

        self.session = get_authenticated_session(username, password)
        self.session.headers.update({'User-Agent': f'{hyp3_sdk.__name__}/{hyp3_sdk.__version__}'})

    def find_jobs(self, start: Optional[datetime] = None, end: Optional[datetime] = None,
                  status_code: Optional[str] = None, name: Optional[str] = None,
                  job_type: Optional[str] = None) -> Batch:
        """Gets a Batch of jobs from HyP3 matching the provided search criteria

        Args:
            start: only jobs submitted after given time
            end: only jobs submitted before given time
            status_code: only jobs matching this status (SUCCEEDED, FAILED, RUNNING, PENDING)
            name: only jobs with this name
            job_type: only jobs with this job_type

        Returns:
            A Batch object containing the found jobs
        """
        params = {}
        for param_name in ('start', 'end', 'status_code', 'name', 'job_type'):
            param_value = locals().get(param_name)
            if param_value is not None:
                if isinstance(param_value, datetime):
                    if param_value.tzinfo is None:
                        param_value = param_value.replace(tzinfo=timezone.utc)
                    param_value = param_value.isoformat(timespec='seconds')

                params[param_name] = param_value

        response = self.session.get(urljoin(self.url, '/jobs'), params=params)
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
        response = self.session.get(urljoin(self.url, f'/jobs/{job_id}'))
        _raise_for_hyp3_status(response)

        return Job.from_dict(response.json())

    @singledispatchmethod
    def watch(self, job_or_batch: Union[Batch, Job], timeout: int = 10800,
              interval: Union[int, float] = 60) -> Union[Batch, Job]:
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
    def _watch_batch(self, batch: Batch, timeout: int = 10800, interval: Union[int, float] = 60) -> Batch:
        tqdm = get_tqdm_progress_bar()
        iterations_until_timeout = math.ceil(timeout / interval)
        bar_format = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{postfix[0]}]'
        with tqdm(total=len(batch), bar_format=bar_format, postfix=[f'timeout in {timeout} s']) as progress_bar:
            for ii in range(iterations_until_timeout):
                batch = self.refresh(batch)

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
    def _watch_job(self, job: Job, timeout: int = 10800, interval: Union[int, float] = 60) -> Job:
        tqdm = get_tqdm_progress_bar()
        iterations_until_timeout = math.ceil(timeout / interval)
        bar_format = '{n_fmt}/{total_fmt} [{postfix[0]}]'
        with tqdm(total=1, bar_format=bar_format, postfix=[f'timeout in {timeout} s']) as progress_bar:
            for ii in range(iterations_until_timeout):
                job = self.refresh(job)
                progress_bar.postfix = [f'timeout in {timeout - ii * interval}s']
                progress_bar.update(int(job.complete()))

                if job.complete():
                    return job
                time.sleep(interval)
        raise HyP3Error(f'Timeout occurred while waiting for {job}')

    @singledispatchmethod
    def refresh(self, job_or_batch: Union[Batch, Job]) -> Union[Batch, Job]:
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
        return Batch(jobs)

    @refresh.register
    def _refresh_job(self, job: Job):
        return self.get_job_by_id(job.job_id)

    def submit_prepared_jobs(self, prepared_jobs: Union[dict, List[dict]]) -> Batch:
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

        response = self.session.post(urljoin(self.url, '/jobs'), json=payload)
        _raise_for_hyp3_status(response)

        batch = Batch()
        for job in response.json()['jobs']:
            batch += Job.from_dict(job)
        return batch

    def submit_autorift_job(self, granule1: str, granule2: str, name: Optional[str] = None) -> Batch:
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
    def prepare_autorift_job(cls, granule1: str, granule2: str, name: Optional[str] = None) -> dict:
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

    def submit_rtc_job(self,
                       granule: str,
                       name: Optional[str] = None,
                       dem_matching: bool = False,
                       include_dem: bool = False,
                       include_inc_map: bool = False,
                       include_rgb: bool = False,
                       include_scattering_area: bool = False,
                       radiometry: Literal['sigma0', 'gamma0'] = 'gamma0',
                       resolution: Literal[30] = 30,
                       scale: Literal['amplitude', 'power'] = 'power',
                       speckle_filter: bool = False,
                       dem_name: Literal['copernicus', 'legacy'] = 'copernicus') -> Batch:
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
            scale: Scale of output image; either power or amplitude
            speckle_filter: Apply an Enhanced Lee speckle filter
            dem_name: Name of the DEM to use for processing.  `copernicus` will use the Copernicus GLO-30 Public DEM,
                while `legacy` will use the DEM with the best coverage from ASF's legacy SRTM/NED datasets.

        Returns:
            A Batch object containing the RTC job
        """
        arguments = locals()
        arguments.pop('self')
        job_dict = self.prepare_rtc_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_rtc_job(cls,
                        granule: str,
                        name: Optional[str] = None,
                        dem_matching: bool = False,
                        include_dem: bool = False,
                        include_inc_map: bool = False,
                        include_rgb: bool = False,
                        include_scattering_area: bool = False,
                        radiometry: Literal['sigma0', 'gamma0'] = 'gamma0',
                        resolution: Literal[30] = 30,
                        scale: Literal['amplitude', 'power'] = 'power',
                        speckle_filter: bool = False,
                        dem_name: Literal['copernicus', 'legacy'] = 'copernicus') -> dict:
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
            scale: Scale of output image; either power or amplitude
            speckle_filter: Apply an Enhanced Lee speckle filter
            dem_name: Name of the DEM to use for processing.  `copernicus` will use the Copernicus GLO-30 Public DEM,
                while `legacy` will use the DEM with the best coverage from ASF's legacy SRTM/NED datasets.

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

    def submit_insar_job(self,
                         granule1: str,
                         granule2: str,
                         name: Optional[str] = None,
                         include_look_vectors: bool = False,
                         include_los_displacement: bool = False,
                         include_inc_map: bool = False,
                         looks: Literal['20x4', '10x2'] = '20x4',
                         include_dem: bool = False,
                         include_wrapped_phase: bool = False,
                         apply_water_mask: bool = False,
                         include_displacement_maps: bool = False) -> Batch:
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

        Returns:
            A Batch object containing the InSAR job
        """
        arguments = locals().copy()
        arguments.pop('self')
        job_dict = self.prepare_insar_job(**arguments)
        return self.submit_prepared_jobs(prepared_jobs=job_dict)

    @classmethod
    def prepare_insar_job(cls,
                          granule1: str,
                          granule2: str,
                          name: Optional[str] = None,
                          include_look_vectors: bool = False,
                          include_los_displacement: bool = False,
                          include_inc_map: bool = False,
                          looks: Literal['20x4', '10x2'] = '20x4',
                          include_dem: bool = False,
                          include_wrapped_phase: bool = False,
                          apply_water_mask: bool = False,
                          include_displacement_maps: bool = False) -> dict:
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
        Returns:
            A dictionary containing the prepared InSAR job
        """
        if include_los_displacement:
            warnings.warn('The include_los_displacement parameter has been deprecated in favor of '
                          'include_displacement_maps, and will be removed in a future release.', FutureWarning)

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

    def my_info(self) -> dict:
        """
        Returns:
            Your user information
        """
        response = self.session.get(urljoin(self.url, '/user'))
        _raise_for_hyp3_status(response)
        return response.json()

    def check_quota(self) -> int:
        """
        Returns:
            The number of jobs left in your quota
        """
        info = self.my_info()
        return info['quota']['remaining']
