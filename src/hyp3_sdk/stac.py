import json
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import fsspec
import pystac
from osgeo import gdal
from shapely import geometry, to_geojson
from tqdm import tqdm


gdal.UseExceptions()

COLLECTION_ID = 'sentinel-1-hyp3-product-stack'
SAR_INSTRUMENT_MODE = 'IW'
SAR_FREQUENCY_BAND = 'C'

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


@dataclass
class ParameterFile:
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
    def read(file_path: Path, base_fs=None):
        file_path = str(file_path)
        if file_path.startswith('https'):
            if base_fs is None:
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
            reference_orbit_number=parameters['Reference Orbit Number'],
            secondary_orbit_direction=parameters['Secondary Pass Direction'],
            secondary_orbit_number=parameters['Secondary Orbit Number'],
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


def jsonify_stac_item(stac_item: dict) -> str:
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime) and obj.tzinfo == timezone.utc:
                return obj.isoformat().removesuffix('+00:00') + 'Z'
            return json.JSONEncoder.default(self, obj)

    return json.dumps(stac_item, cls=DateTimeEncoder)


def get_geotiff_bounding_box_no_gdal(file_path):
    with open(file_path, 'rb') as tiff_file:
        # Read the TIFF header to get the offset to the first IFD (Image File Directory)
        header = tiff_file.read(8)
        (magic_number,) = struct.unpack('HHHH', header)
        if magic_number != 0x4949 and magic_number != 0x4D4D:
            raise ValueError('Not a valid TIFF file.')

        if magic_number == 0x4949:  # Little-endian
            byte_order = '<'
        else:  # Big-endian
            byte_order = '>'

        (offset_to_ifd,) = struct.unpack(byte_order + 'I', tiff_file.read(4))

        # Move to the offset of the first IFD
        tiff_file.seek(offset_to_ifd)

        # Read the number of directory entries
        (num_entries,) = struct.unpack(byte_order + 'H', tiff_file.read(2))

        for _ in range(num_entries):
            tag, field_type, num_values, value_offset = struct.unpack(byte_order + 'HHII', tiff_file.read(12))

            # GeoKeyDirectoryTag (34735) contains the geo-referencing information
            if tag == 34735:
                tiff_file.seek(value_offset)
                geo_keys = struct.unpack(byte_order + 'I' * num_values, tiff_file.read(4 * num_values))

                min_x = geo_keys[10]  # GeoKeyDirectoryTag: ModelTiepointTag
                min_y = geo_keys[11]  # GeoKeyDirectoryTag: ModelTiepointTag
                max_x = min_x + geo_keys[4] * geo_keys[1]  # width * pixel scale in x direction
                max_y = min_y + geo_keys[5] * geo_keys[0]  # height * pixel scale in y direction

                return min_x, min_y, max_x, max_y

        raise ValueError('GeoTIFF metadata not found.')


def get_geotiff_info(file_path):
    dataset = gdal.Open(file_path)
    geotransform = dataset.GetGeoTransform()
    shape = (dataset.RasterXSize, dataset.RasterYSize)
    proj = dataset.GetProjectionRef()
    dataset = None
    return geotransform, shape, proj


def get_bounding_box(geotransform, shape):
    min_x = geotransform[0]
    max_x = min_x + geotransform[1] * shape[0]
    max_y = geotransform[3]
    min_y = max_y + geotransform[5] * shape[1]

    bbox = geometry.box(min_x, min_y, max_x, max_y)
    return bbox


def create_stac_item(product) -> dict:
    base_url = product.to_dict()['files'][0]['url']
    param_file_url = base_url.replace('.zip', '.txt')
    param_file = ParameterFile.read(param_file_url)
    pattern = '%Y%m%dT%H%M%S'
    start_time = datetime.strptime(param_file.reference_granule.split('_')[3], pattern).replace(tzinfo=timezone.utc)
    stop_time = datetime.strptime(param_file.secondary_granule.split('_')[3], pattern).replace(tzinfo=timezone.utc)
    reference_polarization = param_file.reference_granule.split('_')[5]
    secondary_polarization = param_file.secondary_granule.split('_')[5]
    polarizations = list(set([reference_polarization, secondary_polarization]))

    unw_file_url = '/vsicurl/' + base_url.replace('.zip', '_unw_phase.tif')
    geotransform, shape, proj = get_geotiff_info(unw_file_url)
    bbox = get_bounding_box(geotransform, shape)

    properties = {
        'sar:instrument_mode': SAR_INSTRUMENT_MODE,
        'sar:frequency_band': SAR_FREQUENCY_BAND,
        'sar:product_type': product.to_dict()['job_type'],
        'sar:polarizations': polarizations,
        'start_datetime': start_time.isoformat(),
        'end_datetime': stop_time.isoformat(),
    }
    properties.update(param_file.__dict__)
    item = pystac.Item(
        id=base_url.split('/')[-1].replace('.zip', ''),
        geometry=to_geojson(bbox),
        bbox=to_geojson(bbox),
        datetime=start_time,
        properties=properties,
        stac_extensions=['https://stac-extensions.github.io/sar/v1.0.0/schema.json'],
    )
    for asset_type in INSAR_ISCE_BURST_PRODUCTS:
        item.add_asset(
            key=asset_type,
            asset=pystac.Asset(
                href=base_url.replace('.zip', f'_{asset_type}.tif'), media_type=pystac.MediaType.GEOTIFF
            ),
        )
    return item


def create_stac_catalog(products, out_path, id='hyp3_jobs'):
    catalog = pystac.Catalog(id=id, description='A catalog of Hyp3 jobs')
    for product in tqdm(products):
        item = create_stac_item(product)
        catalog.add_item(item)
    catalog.normalize_hrefs(str(out_path))
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
