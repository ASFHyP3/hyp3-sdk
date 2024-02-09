"""A module for creating STAC collections based on HyP3-SDK Batch/Job objects"""
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import fsspec
import pystac
from PIL import Image
from PIL.TiffTags import TAGS
from pystac import Extent, ProviderRole, SpatialExtent, Summaries, TemporalExtent
from pystac.extensions import sar
from pystac.extensions.projection import ProjectionExtension
from pystac.extensions.raster import RasterExtension
from pystac.extensions.sar import SarExtension
from tqdm import tqdm

from hyp3_sdk import Batch, Job


SENTINEL_CONSTELLATION = 'sentinel-1'
SENTINEL_PLATFORMS = ['sentinel-1a', 'sentinel-1b']
SENTINEL_PROVIDER = pystac.Provider(
    name='ESA',
    roles=[ProviderRole.LICENSOR, ProviderRole.PRODUCER],
    url='https://sentinel.esa.int/web/sentinel/missions/sentinel-1',
)
SENTINEL_BURST_PROVIDER = pystac.Provider(
    name='ASF DAAC',
    roles=[ProviderRole.LICENSOR, ProviderRole.PROCESSOR, ProviderRole.HOST],
    url='https://hyp3-docs.asf.alaska.edu/guides/burst_insar_product_guide/',
    extra_fields={
        'processing:level': 'L3',
        'processing:lineage': 'ASF DAAC HyP3 2023 using the hyp3_isce2 plugin version 0.9.1 running ISCE release 2.6.3',  # noqa: E501
        'processing:software': {'ISCE2': '2.6.3'},
    },
)
SENTINEL_BURST_DESCRIPTION = 'SAR Interferometry (InSAR) products and their associated files. The source data for these products are Sentinel-1 bursts, extracted from Single Look Complex (SLC) products processed by ESA, and they were processed using InSAR Scientific Computing Environment version 2 (ISCE2) software.'  # noqa: E501
INSAR_ISCE_BURST_PRODUCTS = [
    'conncomp',
    'corr',
    'unw_phase',
    'wrapped_phase',
    'lv_phi',
    'lv_theta',
    'dem',
    'water_mask',
]

# RTC_PRODUCTS = ['VV', 'VH', 'HH' 'HV', 'rgb', 'area', 'dem', 'inc_map', 'ls_map']


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
                base_fs = fsspec.filesystem('https', block_size=5 * (2**20))
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


def get_utm_epsg(proj_str: str) -> int:
    """Get the EPSG code for the UTM zone from a TIFF projection string

    Args:
        proj_str: The projection string from a TIFF file

    Returns:
        The EPSG code for the UTM zone
    """
    pattern = r'WGS 84 \/ UTM zone (\d{1,2}[SN])\|WGS 84\|'
    match = re.search(pattern, proj_str)
    if match is None:
        raise ValueError(f'Invalid projection string: {proj_str}')
    utm_str = match.group(1)

    epsg_code = 32600
    epsg_code += int(utm_str[:-1])
    if utm_str[-1] == 'S':
        epsg_code += 100
    return int(epsg_code)


def get_geotiff_info_nogdal(file_path: Path, base_fs: Optional[fsspec.AbstractFileSystem] = None) -> Tuple:
    """Get geotiff projection info without using GDAL

    Args:
        file_path: Path to the geotiff file
        base_fs: fsspec filesystem to use for reading the file

    Returns:
        A tuple containing the geotransform, shape, and EPSG code
    """
    if base_fs is None:
        if file_path.startswith('https'):
            base_fs = fsspec.filesystem('https', block_size=5 * (2**20))
        else:
            base_fs = fsspec.filesystem('file')

    with base_fs.open(file_path, 'rb') as file:
        image = Image.open(file)
        meta_dict = {TAGS[key]: image.tag[key] for key in image.tag_v2}

    width = int(meta_dict['ImageWidth'][0])
    length = int(meta_dict['ImageLength'][0])
    pixel_x, pixel_y = meta_dict['ModelPixelScaleTag'][:2]
    pixel_y *= -1
    origin_x, origin_y = meta_dict['ModelTiepointTag'][3:5]
    geotransform = [int(value) for value in [origin_x, pixel_x, 0, origin_y, 0, pixel_y]]
    proj_str = meta_dict['GeoAsciiParamsTag'][0]
    utm_epsg = get_utm_epsg(proj_str)
    return geotransform, (length, width), utm_epsg


# def get_geotiff_info(file_path):
#     dataset = gdal.Open(file_path)
#     geotransform = list(dataset.GetGeoTransform())
#     shape = (dataset.RasterXSize, dataset.RasterYSize)
#     proj = osr.SpatialReference(wkt=dataset.GetProjection())
#     utm_epsg = int(proj.GetAttrValue('AUTHORITY', 1))
#     dataset = None
#     return geotransform, shape, utm_epsg


def get_bounding_box(geotransform: Iterable, shape: Iterable) -> List:
    """Get the bounding box for a given geotransform and shape

    Args:
        geotransform: A gdal geotransform
        shape: The shape of the associated raster

    Returns:
        A list containing the bounding box coordinates (min_x, min_y, max_x, max_y)
    """
    length, width = shape
    min_x = geotransform[0]
    max_x = min_x + geotransform[1] * length
    max_y = geotransform[3]
    min_y = max_y + geotransform[5] * width

    bbox = [min_x, min_y, max_x, max_y]
    return bbox


def get_overall_bbox(bboxes: Iterable) -> List:
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


def bounding_box_to_geojson(minx, miny, maxx, maxy) -> dict:
    """Convert bounding box coordinates to GeoJSON Polygon

    Args:
        minx: Minimum x coordinate
        miny: Minimum y coordinate
        maxx: Maximum x coordinate
        maxy: Maximum y coordinate

    Returns:
        A GeoJSON Polygon
    """
    polygon = {
        'type': 'Polygon',
        'coordinates': [
            [
                [minx, miny],
                [maxx, miny],
                [maxx, maxy],
                [minx, maxy],
                [minx, miny],
            ]
        ],
    }
    return polygon


def to_proj_geotransform(gdal_geotransform: List) -> Tuple:
    """Convert a GDAL geotransform to a proj geotransform

    Args:
        geotransform: A GDAL geotransform

    Returns:
        A rasterio geotransform
    """
    proj_transform = [
        gdal_geotransform[1],
        gdal_geotransform[2],
        gdal_geotransform[0],
        gdal_geotransform[4],
        gdal_geotransform[5],
        gdal_geotransform[3],
        0,
        0,
        1,
    ]
    return proj_transform


def validate_stack(batch: Batch) -> None:
    """Verifies that all jobs in batch:
    - Have the SUCCEEDED status
    - Have the same job type
    - Have the same processing parameters
    Notably DOES NOT check that all jobs are co-located.

    Args:
        batch: A HyP3 Batch object
    """
    job_dicts = [job.to_dict() for job in batch]
    n_success = [job['status_code'] == 'SUCCEEDED' for job in job_dicts].count(True)
    if n_success != len(batch):
        raise ValueError('Not all jobs in the batch have succeeded yet')

    job_types = list(set([job['job_type'] for job in job_dicts]))
    if len(job_types) != 1:
        raise ValueError(f'Not all jobs have the same job type. Included types: {" ".join(job_types)}')

    job_params = [job['job_parameters'] for job in job_dicts]
    [job.pop('granules', None) for job in job_params]
    param_set = list(set([str(job) for job in job_params]))
    if len(param_set) != 1:
        raise ValueError('Not all jobs have the same processing parameters')


def create_insar_stac_item(job: Job) -> pystac.Item:
    """Create a STAC item from a HyP3 product

    Args:
        product: A HyP3 Job object representing the product

    Returns:
        A STAC item for the product
    """
    base_url = job.to_dict()['files'][0]['url']
    param_file_url = base_url.replace('.zip', '.txt')
    param_file = ParameterFile.read(param_file_url)

    unw_file_url = base_url.replace('.zip', '_unw_phase.tif')
    geotransform, shape, epsg = get_geotiff_info_nogdal(unw_file_url)
    bbox = get_bounding_box(geotransform, shape)

    pattern = '%Y%m%dT%H%M%S'
    start_time = datetime.strptime(param_file.reference_granule.split('_')[3], pattern).replace(tzinfo=timezone.utc)
    stop_time = datetime.strptime(param_file.secondary_granule.split('_')[3], pattern).replace(tzinfo=timezone.utc)
    reference_polarization = param_file.reference_granule.split('_')[4]
    secondary_polarization = param_file.secondary_granule.split('_')[4]
    polarizations = list(set([reference_polarization, secondary_polarization]))

    # If you're using GDAL to get the geotiff info, you can use this code
    # unw_file_url = '/vsicurl/' + base_url.replace('.zip', '_unw_phase.tif')
    # geotransform, shape, epsg = get_geotiff_info(unw_file_url)

    properties = {
        'data_type': 'float32',
        'nodata': 0,
        'proj:shape': shape,
        'proj:transform': to_proj_geotransform(geotransform),
        'proj:epsg': epsg,
        'sar:instrument_mode': 'IW',
        'sar:frequency_band': sar.FrequencyBand.C,
        'sar:product_type': job.to_dict()['job_type'],
        'sar:polarizations': polarizations,
        'start_datetime': start_time.isoformat(),
        'end_datetime': stop_time.isoformat(),
    }
    properties.update(param_file.__dict__)
    item = pystac.Item(
        id=base_url.split('/')[-1].replace('.zip', ''),
        geometry=bounding_box_to_geojson(*bbox),
        bbox=bbox,
        datetime=start_time,
        properties=properties,
        stac_extensions=[
            RasterExtension.get_schema_uri(),
            ProjectionExtension.get_schema_uri(),
            SarExtension.get_schema_uri(),
        ],
    )
    for asset_type in INSAR_ISCE_BURST_PRODUCTS:
        item.add_asset(
            key=asset_type,
            asset=pystac.Asset(
                href=base_url.replace('.zip', f'_{asset_type}.tif'),
                media_type=pystac.MediaType.GEOTIFF,
                roles=['data'],
            ),
        )

    item.add_asset(
        key='browse',
        asset=pystac.Asset(href=job.browse_images[0], media_type=pystac.MediaType.PNG, roles=['overview']),
    )
    item.add_asset(
        key='thumbnail',
        asset=pystac.Asset(href=job.thumbnail_images[0], media_type=pystac.MediaType.PNG, roles=['thumbnail']),
    )
    item.add_asset(
        key='metadata', asset=pystac.Asset(href=param_file_url, media_type=pystac.MediaType.TEXT, roles=['metadata'])
    )
    item.validate()
    return item


def create_stac_collection(batch: Batch, out_path: Path, collection_id: str = 'hyp3_jobs') -> None:
    """Create a STAC collection from a HyP3 batch and save it to a directory

    Args:
        batch: A HyP3 Batch object, or a list of jobs
        out_path: Path to the directory where the STAC collection will be saved
        id: The ID of the STAC catalog
    """
    validate_stack(batch)
    items = []
    dates = []
    bboxes = []
    for job in tqdm(batch):
        item = create_insar_stac_item(job)
        items.append(item)
        dates.append(item.datetime)
        bboxes.append(item.bbox)

    extent = Extent(SpatialExtent(get_overall_bbox(bboxes)), TemporalExtent([[min(dates), max(dates)]]))
    summary_dict = {'constellation': [SENTINEL_CONSTELLATION], 'platform': SENTINEL_PLATFORMS}

    collection = pystac.Collection(
        id=collection_id,
        description=SENTINEL_BURST_DESCRIPTION,
        extent=extent,
        keywords=['sentinel', 'copernicus', 'esa', 'sar'],
        providers=[SENTINEL_PROVIDER, SENTINEL_BURST_PROVIDER],
        summaries=Summaries(summary_dict),
        title='ASF S1 BURST INTERFEROGRAMS',
    )
    [collection.add_item(item) for item in items]
    collection.normalize_hrefs(str(out_path))
    collection.validate()
    collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
