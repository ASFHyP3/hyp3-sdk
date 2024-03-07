"""A module for creating STAC collections based on HyP3-SDK Batch/Job objects"""
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from tqdm import tqdm

from hyp3_sdk import Batch, Job


missing_modules = []
try:
    import pystac
    from pystac.extensions import projection, raster, sar
except ImportError:
    missing_modules.append('pystac')

try:
    import fsspec
except ImportError:
    missing_modules.append('fsspec')

try:
    import tifffile
except ImportError:
    missing_modules.append('tifffile')

if missing_modules:
    raise ImportError(f'package(s) {" ,".join(missing_modules)} is/are required for this module')

SENTINEL_CONSTELLATION = 'sentinel-1'
SENTINEL_PLATFORMS = ['sentinel-1a', 'sentinel-1b']
SENTINEL_PROVIDER = pystac.Provider(
    name='ESA',
    roles=[pystac.ProviderRole.LICENSOR, pystac.ProviderRole.PRODUCER],
    url='https://sentinel.esa.int/web/sentinel/missions/sentinel-1',
)
HYP3_PROVIDER = pystac.Provider(
    name='ASF DAAC',
    roles=[pystac.ProviderRole.LICENSOR, pystac.ProviderRole.PROCESSOR, pystac.ProviderRole.HOST],
    url='https://hyp3-docs.asf.alaska.edu/',
    extra_fields={'processing:level': 'L3', 'processing:lineage': 'ASF DAAC HyP3 2023'},
)
SENTINEL_DATA_DESCRIPTION = (
    'HyP3 genereted Sentinel-1 SAR products and their associated files.'
    ' The source data for these products are Sentinel-1 Single Look Complex (SLC) products processed by ESA'
)

RTC_PRODUCTS = ['rgb', 'area', 'dem', 'inc_map', 'ls_map']


@dataclass
class ParameterFile:
    """Class representing the parameters of a HyP3 InSAR product"""

    reference_granule: str
    secondary_granule: str
    reference_orbit_direction: str
    reference_orbit_number: str
    secondary_orbit_direction: str
    secondary_orbit_number: str
    baseline: float
    utc_time: float
    heading: float
    spacecraft_height: float
    earth_radius_at_nadir: float
    slant_range_near: float
    slant_range_center: float
    slant_range_far: float
    range_looks: int
    azimuth_looks: int
    insar_phase_filter: bool
    phase_filter_parameter: float
    range_bandpass_filter: bool
    azimuth_bandpass_filter: bool
    dem_source: str
    dem_resolution: int
    unwrapping_type: str
    speckle_filter: bool
    water_mask: bool

    def __str__(self):
        output_strings = [
            f'Reference Granule: {self.reference_granule}\n',
            f'Secondary Granule: {self.secondary_granule}\n',
            f'Reference Pass Direction: {self.reference_orbit_direction}\n',
            f'Reference Orbit Number: {self.reference_orbit_number}\n',
            f'Secondary Pass Direction: {self.secondary_orbit_direction}\n',
            f'Secondary Orbit Number: {self.secondary_orbit_number}\n',
            f'Baseline: {self.baseline}\n',
            f'UTC time: {self.utc_time}\n',
            f'Heading: {self.heading}\n',
            f'Spacecraft height: {self.spacecraft_height}\n',
            f'Earth radius at nadir: {self.earth_radius_at_nadir}\n',
            f'Slant range near: {self.slant_range_near}\n',
            f'Slant range center: {self.slant_range_center}\n',
            f'Slant range far: {self.slant_range_far}\n',
            f'Range looks: {self.range_looks}\n',
            f'Azimuth looks: {self.azimuth_looks}\n',
            f'INSAR phase filter: {"yes" if self.insar_phase_filter else "no"}\n',
            f'Phase filter parameter: {self.phase_filter_parameter}\n',
            f'Range bandpass filter: {"yes" if self.range_bandpass_filter else "no"}\n',
            f'Azimuth bandpass filter: {"yes" if self.azimuth_bandpass_filter else "no"}\n',
            f'DEM source: {self.dem_source}\n',
            f'DEM resolution (m): {self.dem_resolution}\n',
            f'Unwrapping type: {self.unwrapping_type}\n',
            f'Speckle filter: {"yes" if self.speckle_filter else "no"}\n',
            f'Water mask: {"yes" if self.water_mask else "no"}\n',
        ]

        return ''.join(output_strings)

    def __repr__(self):
        return self.__str__()

    def write(self, out_path: Path):
        out_path.write_text(self.__str__())

    @staticmethod
    def read(file_path: Path, base_fs: Optional[fsspec.AbstractFileSystem] = None) -> 'ParameterFile':
        """Read a HyP3 InSAR parameter file

        Args:
            file_path: Path to the parameter file
            base_fs: fsspec filesystem to use for reading the file

        Returns:
            A parameter file object
        """
        file_path = str(file_path)
        if base_fs is None:
            if file_path.startswith('https'):
                base_fs = fsspec.filesystem('https', block_size=int(0.1 * (2**20)))
            else:
                base_fs = fsspec.filesystem('file')

        with base_fs.open(file_path, 'r') as file:
            text = file.read().strip()

        parameters = {}
        for line in text.split('\n'):
            key, *values = line.strip().split(':')
            value = values[0].replace(' ', '')
            parameters[key] = value

        param_file = ParameterFile(
            reference_granule=parameters['Reference Granule'],
            secondary_granule=parameters['Secondary Granule'],
            reference_orbit_direction=parameters['Reference Pass Direction'],
            reference_orbit_number=int(parameters['Reference Orbit Number']),
            secondary_orbit_direction=parameters['Secondary Pass Direction'],
            secondary_orbit_number=int(parameters['Secondary Orbit Number']),
            baseline=float(parameters['Baseline']),
            utc_time=float(parameters['UTC time']),
            heading=float(parameters['Heading']),
            spacecraft_height=float(parameters['Spacecraft height']),
            earth_radius_at_nadir=float(parameters['Earth radius at nadir']),
            slant_range_near=float(parameters['Slant range near']),
            slant_range_center=float(parameters['Slant range center']),
            slant_range_far=float(parameters['Slant range far']),
            range_looks=int(parameters['Range looks']),
            azimuth_looks=int(parameters['Azimuth looks']),
            insar_phase_filter=parameters['INSAR phase filter'] == 'yes',
            phase_filter_parameter=float(parameters['Phase filter parameter']),
            range_bandpass_filter=parameters['Range bandpass filter'] == 'yes',
            azimuth_bandpass_filter=parameters['Azimuth bandpass filter'] == 'yes',
            dem_source=parameters['DEM source'],
            dem_resolution=int(parameters['DEM resolution (m)']),
            unwrapping_type=parameters['Unwrapping type'],
            speckle_filter=parameters['Speckle filter'] == 'yes',
            water_mask=True,
        )

        return param_file


@dataclass
class GeoInfo:
    """Class representing the geospatial information of a geotiff file"""

    transform: Tuple[float]
    shape: Tuple[int]  # y first
    epsg: int

    def __post_init__(self):
        """Add bounding box, bounding box geojson, and proj_transform attributes"""
        length, width = self.shape
        min_x, size_x, _, max_y, _, size_y = self.transform
        max_x = min_x + size_x * width
        min_y = max_y + size_y * length
        bbox = [min_x, min_y, max_x, max_y]
        self.bbox = bbox

        bbox_geojson = {
            'type': 'Polygon',
            'coordinates': [
                [
                    [min_x, min_y],
                    [max_x, min_y],
                    [max_x, max_y],
                    [min_x, max_y],
                    [min_x, min_y],
                ]
            ],
        }
        self.bbox_geojson = bbox_geojson

        proj_transform = [
            self.transform[1],
            self.transform[2],
            self.transform[0],
            self.transform[4],
            self.transform[5],
            self.transform[3],
            0,
            0,
            1,
        ]
        self.proj_transform = proj_transform


def get_epsg(geo_key_list: Iterable[int]) -> int:
    """Get the EPSG code from a GeoKeyDirectoryTag.
    Will only workfor projected coordinate systems.

    Args:
        geo_key_list: A list of GeoKeyDirectoryTag values

    Returns:
        The EPSG code for the projected coordinate system
    """
    projected_crs_key_id = 3072
    geo_keys = [geo_key_list[i: i + 4] for i in range(0, len(geo_key_list), 4)]
    for key in geo_keys:
        if key[0] == projected_crs_key_id:
            return int(key[3])

    raise ValueError('No projected EPSG code found in GeoKeyDirectoryTag')


def get_geotiff_info_nogdal(file_path: str, base_fs: Optional[fsspec.AbstractFileSystem] = None) -> GeoInfo:
    """Get geotiff projection info without using GDAL.

    Args:
        file_path: Path to the geotiff file
        base_fs: fsspec filesystem to use for reading the file

    Returns:
        A GeoInfo object containing the geospatial information
    """
    # Tag IDs from the TIFF and GeoTIFF specs
    # https://www.itu.int/itudoc/itu-t/com16/tiff-fx/docs/tiff6.pdf
    # https://docs.ogc.org/is/19-008r4/19-008r4.html
    tag_ids = {
        'ImageWidth': 256,
        'ImageLength': 257,
        'ModelPixelScaleTag': 33550,
        'ModelTiepointTag': 33922,
        'GeoKeyDirectoryTag': 34735,
    }
    if base_fs is None:
        if file_path.startswith('https'):
            base_fs = fsspec.filesystem('https', block_size=int(0.1 * (2**20)))
        else:
            base_fs = fsspec.filesystem('file')

    meta_dict = {}
    with base_fs.open(file_path, 'rb') as file:
        with tifffile.TiffFile(file) as tif:
            tags = tif.pages[0].tags
            for key, value in tag_ids.items():
                meta_dict[key] = tags[value].value

    width = int(meta_dict['ImageWidth'])
    length = int(meta_dict['ImageLength'])
    pixel_x, pixel_y = meta_dict['ModelPixelScaleTag'][:2]
    pixel_y *= -1
    origin_x, origin_y = meta_dict['ModelTiepointTag'][3:5]
    geotransform = [int(value) for value in [origin_x, pixel_x, 0, origin_y, 0, pixel_y]]
    utm_epsg = get_epsg(meta_dict['GeoKeyDirectoryTag'])
    geo_info = GeoInfo(geotransform, (length, width), utm_epsg)
    return geo_info


def get_overall_bbox(bboxes: Iterable[float]) -> List[float]:
    """Get the overall bounding box for a list of bounding boxes

    Args:
        bboxes: A list of bounding boxes

    Returns:
        A list containing the overall bounding box coordinates (min_x, min_y, max_x, max_y)
    """
    min_x = min([bbox[0] for bbox in bboxes])
    min_y = min([bbox[1] for bbox in bboxes])
    max_x = max([bbox[2] for bbox in bboxes])
    max_y = max([bbox[3] for bbox in bboxes])
    return [min_x, min_y, max_x, max_y]


def validate_stack(batch: Batch) -> None:
    """Verifies that all jobs in batch:
    - Have the SUCCEEDED status
    - Are not expired
    - Have the same job type
    - The job type is one of INSAR_GAMMA, RTC_GAMMA, INSAR
    - Have the same processing parameters
    Notably DOES NOT check that all jobs are co-located.

    Args:
        batch: A HyP3 Batch object
    """
    job_dicts = [job.to_dict() for job in batch]
    n_success = [job['status_code'] == 'SUCCEEDED' for job in job_dicts].count(True)
    if n_success != len(batch):
        raise ValueError('Not all jobs in the batch have succeeded yet')

    if batch.any_expired():
        raise ValueError('Some of the jobs in the batch have expired')

    job_types = list(set([job['job_type'] for job in job_dicts]))
    if len(job_types) != 1:
        raise ValueError(f'Not all jobs have the same job type. Included types: {" ".join(job_types)}')

    supported_job_types = ['INSAR_GAMMA', 'RTC_GAMMA', 'INSAR_ISCE_BURST']
    if job_types[0] not in supported_job_types:
        msg = f'Job type {job_types[0]} is not supported. Only {" ,".join(supported_job_types)} are supported'
        raise NotImplementedError(msg)

    job_params = [job['job_parameters'] for job in job_dicts]
    [job.pop('granules', None) for job in job_params]
    param_set = list(set([str(job) for job in job_params]))
    if len(param_set) != 1:
        raise ValueError('Not all jobs have the same processing parameters')


def write_item(item):
    item_dict = item.to_dict(include_self_link=False, transform_hrefs=False)
    with open(f'{item.id}.json', 'w') as f:
        f.write(json.dumps(item_dict))


def create_insar_stac_item(job: Job, geo_info: GeoInfo, param_file: ParameterFile) -> pystac.Item:
    """Create a STAC item from a HyP3 product.

    Args:
        job: A HyP3 Job object
        geo_info: A GeoInfo object containing the geospatial information of the product
        param_file: A ParameterFile object containing the processing parameters of the product

    Returns:
        A STAC item for the product
    """
    base_url = job.to_dict()['files'][0]['url']

    insar_products = ['corr', 'unw_phase', 'lv_phi', 'lv_theta', 'dem', 'water_mask']
    if job.to_dict()['job_type'] == 'INSAR_GAMMA':
        date_loc = 5
        reference_polarization = 'VV'
        secondary_polarization = 'VV'
    elif job.to_dict()['job_type'] == 'INSAR_ISCE_BURST':
        date_loc = 3
        reference_polarization = param_file.reference_granule.split('_')[4]
        secondary_polarization = param_file.secondary_granule.split('_')[4]
        insar_products += ['conncomp', 'wrapped_phase']

    pattern = '%Y%m%dT%H%M%S'
    start_time = datetime.strptime(param_file.reference_granule.split('_')[date_loc], pattern).replace(
        tzinfo=timezone.utc
    )
    stop_time = datetime.strptime(param_file.secondary_granule.split('_')[date_loc], pattern).replace(
        tzinfo=timezone.utc
    )
    mid_time = start_time + ((stop_time - start_time) / 2)
    mid_time = mid_time.replace(tzinfo=timezone.utc)
    polarizations = list(set([reference_polarization, secondary_polarization]))

    extra_properies = {
        'sar:product_type': job.to_dict()['job_type'],
        'sar:polarizations': polarizations,
        'start_datetime': start_time.isoformat(),
        'end_datetime': stop_time.isoformat(),
    }
    extra_properies.update(param_file.__dict__)

    item = create_item(base_url, mid_time, geo_info, insar_products, extra_properies)
    thumbnail = base_url.replace('.zip', '_unw_phase.png')
    item.add_asset(
        key='thumbnail',
        asset=pystac.Asset(href=thumbnail, media_type=pystac.MediaType.PNG, roles=['thumbnail']),
    )
    # item.validate()
    return item


def create_rtc_stac_item(job: Job, geo_info: GeoInfo, available_polarizations: Iterable[str]) -> pystac.Item:
    """Create a STAC item from a HyP3 RTC product.

    Args:
        job: A HyP3 Job object
        geo_info: A GeoInfo object containing the geospatial information of the product
        available_polarizations: A list of the available polarizations

    Returns:
        A STAC item for the product
    """
    base_url = job.to_dict()['files'][0]['url']
    pattern = '%Y%m%dT%H%M%S'
    date_string = base_url.split('/')[-1].split('_')[2].split('.')[0]
    start_time = datetime.strptime(date_string, pattern).replace(tzinfo=timezone.utc)
    extra_properties = {'sar:product_type': job.to_dict()['job_type'], 'sar:polarizations': available_polarizations}
    item = create_item(base_url, start_time, geo_info, available_polarizations + RTC_PRODUCTS, extra_properties)
    thumbnail = base_url.replace('.zip', '_rgb_thumb.png')
    item.add_asset(
        key='thumbnail',
        asset=pystac.Asset(href=thumbnail, media_type=pystac.MediaType.PNG, roles=['thumbnail']),
    )
    item.validate()
    return item


def create_item(
    base_url: str, start_time: datetime, geo_info: GeoInfo, product_types: Iterable[str], extra_properties: dict
) -> pystac.Item:
    """Create a STAC item from a HyP3 product.

    Args:
        base_url: The base url for the product
        start_time: The start time of the product
        geo_info: A GeoInfo object containing the geospatial information of the product
        product_types: A list of the product types available
        extra_properties: A dictionary of extra properties to add to the STAC item

    Returns:
        A STAC item for the product
    """
    properties = {
        'data_type': 'float32',
        'nodata': 0,
        'proj:shape': geo_info.shape,
        'proj:transform': geo_info.proj_transform,
        'proj:epsg': geo_info.epsg,
        'sar:instrument_mode': 'IW',
        'sar:frequency_band': sar.FrequencyBand.C,
    }
    properties.update(extra_properties)
    item = pystac.Item(
        id=base_url.split('/')[-1].replace('.zip', ''),
        geometry=geo_info.bbox_geojson,
        bbox=geo_info.bbox,
        datetime=start_time,
        properties=properties,
        stac_extensions=[
            raster.RasterExtension.get_schema_uri(),
            projection.ProjectionExtension.get_schema_uri(),
            sar.SarExtension.get_schema_uri(),
        ],
    )
    for asset_type in product_types:
        item.add_asset(
            key=asset_type,
            asset=pystac.Asset(
                href=base_url.replace('.zip', f'_{asset_type}.tif'),
                media_type=pystac.MediaType.GEOTIFF,
                roles=['data'],
            ),
        )
    return item


def get_insar_info(job: Job) -> Tuple[GeoInfo, ParameterFile]:
    """Get the geospatial and parameter information for an InSAR job.
    Includes all https requests needed to get job info.

    Args:
        job: A HyP3 Job object

    Returns:
        A tuple containing the geospatial information and parameter file
    """
    base_url = job.to_dict()['files'][0]['url']
    unw_file_url = base_url.replace('.zip', '_unw_phase.tif')
    param_file_url = base_url.replace('.zip', '.txt')

    base_fs = fsspec.filesystem('https', block_size=int(0.1 * (2**20)))
    geo_info = get_geotiff_info_nogdal(unw_file_url, base_fs)
    param_file = ParameterFile.read(param_file_url, base_fs)
    return geo_info, param_file


def get_rtc_info(job: Job) -> Tuple[GeoInfo, List[str]]:
    """Get the geospatial and polarization information for an RTC job.
    Includes all https requests needed to get job info.

    Args:
        job: A HyP3 Job object

    Returns:
        A tuple containing the geospatial information and available polarizations
    """
    base_url = job.to_dict()['files'][0]['url']
    base_fs = fsspec.filesystem('https', block_size=int(0.1 * (2**20)))
    available_pols = []
    # FIXME: This would be more efficient if I can get an ls command to work
    for pol in ['VV', 'VH', 'HH', 'HV']:
        url = base_url.replace('.zip', f'_{pol}.tif')
        if base_fs.exists(url):
            available_pols.append(pol)

    first_pol_url = base_url.replace('.zip', f'_{available_pols[0]}.tif')
    geo_info = get_geotiff_info_nogdal(first_pol_url, base_fs)
    return geo_info, available_pols


def create_stac_collection(batch: Batch, out_path: Path, collection_id: str = 'hyp3_jobs', workers: int = 10) -> None:
    """Create a STAC collection from a HyP3 batch and save it to a directory.

    Args:
        batch: A HyP3 Batch object, or a list of jobs
        out_path: Path to the directory where the STAC collection will be saved
        id: The ID of the STAC catalog
        workers: The number of concurent requests to make when getting job info
    """
    validate_stack(batch)

    job_type = batch[0].to_dict()['job_type']
    if 'INSAR' in job_type:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(tqdm(executor.map(get_insar_info, batch), total=len(batch)))
        items = [create_insar_stac_item(job, geo, param) for job, (geo, param) in zip(batch, results)]
    elif 'RTC' in job_type:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = list(tqdm(executor.map(get_rtc_info, batch), total=len(batch)))
        items = [create_rtc_stac_item(job, geo, pols) for job, (geo, pols) in zip(batch, results)]

    bboxes = [item.bbox for item in items]
    dates = [item.datetime for item in items]

    extent = pystac.Extent(
        pystac.SpatialExtent(get_overall_bbox(bboxes)), pystac.TemporalExtent([[min(dates), max(dates)]])
    )
    summary_dict = {'constellation': [SENTINEL_CONSTELLATION], 'platform': SENTINEL_PLATFORMS}

    collection = pystac.Collection(
        id=collection_id,
        description=SENTINEL_DATA_DESCRIPTION,
        extent=extent,
        keywords=['sentinel', 'copernicus', 'esa', 'sar'],
        providers=[SENTINEL_PROVIDER, HYP3_PROVIDER],
        summaries=pystac.Summaries(summary_dict),
        title='ASF HyP3 Products',
    )
    [collection.add_item(item) for item in items]
    collection.normalize_hrefs(str(out_path))
    # collection.validate()
    collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
