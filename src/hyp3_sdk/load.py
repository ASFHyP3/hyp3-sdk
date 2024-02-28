import datetime as dt
import time
from pathlib import Path
from typing import Iterable, Optional, Tuple

import dask
import h5py
import numpy as np
import pystac
import stackstac
import utm
import xarray as xr
from osgeo import osr


osr.UseExceptions()

SPEED_OF_LIGHT = 299792458  # m/s
SENTINEL1 = {
    'carrier_frequency': 5.405e9,  # Hz
    'altitude': 705e3,  # m, mean value
    'antenna_length': 12.3,  # m
    'antenna_width': 0.82,  # m
    'doppler_bandwidth': 380,  # Hz
    'pulse_repetition_frequency': 1717.13,  # Hz, based on real data; 1000-3000 (programmable)
    'chirp_bandwidth': 56.50e6,  # Hz
    'sampling_frequency': 64.35e6,  # Hz
    'azimuth_pixel_size': 14.1,  # m, this is the ground azimuth pixel spacing, NOT on orbits!
    'range_pixel_size': 2.3,  # m
    'ground_range_pixel_size': 4.1,  # m
    'IW1': {'range_resolution': 2.7, 'azimuth_resolution': 22.5},
    'IW2': {'range_resolution': 3.1, 'azimuth_resolution': 22.7},
    'IW3': {'range_resolution': 3.5, 'azimuth_resolution': 22.6},
}


def incidence_angle2slant_range_distance(
    spacecraft_height: float, earth_radius: float, inc_angle: np.ndarray
) -> np.ndarray:
    """Calculate the corresponding slant range distance given an incidence angle.
    Originally created by Zhang Yunjun and the MintPy team.

    Law of sines:
               r + H                   r               range_dist
       --------------------- = ----------------- = ------------------ = 2R
        sin(pi - inc_angle)     sin(look_angle)     sin(range_angle)

    where range_angle = inc_angle - look_angle
          R is the radius of the circumcircle.

    Args:
        earth_radius: radius of the Earth
        spacecraft_height: height of the spacecraft
        inc_angle: incidence angle in degree

    Returns:
        slant range distance array
    """
    inc_angle = inc_angle / 180 * np.pi
    earth_radius = float(earth_radius)
    spacecraft_height = float(spacecraft_height)

    # calculate 2R based on the law of sines
    r2 = (earth_radius + spacecraft_height) / np.sin(np.pi - inc_angle)

    look_angle = np.arcsin(earth_radius / r2)
    range_angle = inc_angle - look_angle
    range_dist = r2 * np.sin(range_angle)

    return range_dist


def utm2latlon(utm_zone: str, easting: float, northing: float) -> (float, float):
    """Convert UTM easting/northing in meters to lat/lon in degrees.
    Originally created by Zhang Yunjun and the MintPy team.

    Args:
        utm_zone: UTM zone number and letter
        easting: UTM easting in meters
        northing: UTM northing in meters

    Returns:
        lat, lon: latitude and longitude in degrees
    """

    zone_num = int(utm_zone[:-1])
    northern = utm_zone[-1].upper() == 'N'
    # set 'strict=False' to allow coordinates outside the range of a typical single UTM zone,
    # which can be common for large area analysis, e.g. the Norwegian mapping authority
    # publishes a height data in UTM zone 33 coordinates for the whole country, even though
    # most of it is technically outside zone 33.
    lat, lon = utm.to_latlon(easting, northing, zone_num, northern=northern, strict=False)
    return lat, lon


def wrap(data: np.ndarray, wrap_range: Optional[Tuple] = [-1.0 * np.pi, np.pi]) -> np.ndarray:
    """Wrap data into a range.
    Originally created by Zhang Yunjun and the MintPy team.

    Args:
        data: data to be wrapped
        wrap_range: range to be wrapped into

    Returns:
        wrapped data
    """
    w0, w1 = wrap_range
    data = w0 + np.mod(data - w0, w1 - w0)
    return data


def get_metadata(dataset: xr.Dataset) -> (dict, list, np.ndarray):
    """Extract metadata from a Xarray dataset of HyP3 InSAR products and return MintPy compatible metadata.

    Args:
        dataset: Xarray dataset of HyP3 InSAR products

    Returns:
        meta: dictionary with metadata
        date12s: list of date pairs
        perp_baseline: array of perpendicular baselines
    """
    keys = list(dataset.coords.keys())
    hyp3_meta = {}
    for key in keys:
        if key in ['time', 'x', 'y', 'band']:
            continue

        value = dataset.coords[key].values
        if value.shape == ():
            value = value.item()
        else:
            value = list(value)

        hyp3_meta[key] = value

    # Add geospatial metadata
    meta = {}
    n_dates, n_bands, meta['LENGTH'], meta['WIDTH'] = dataset.shape
    example_image = dataset.isel(time=0)
    meta['X_FIRST'] = dataset.coords['x'].to_numpy()[0]
    meta['Y_FIRST'] = dataset.coords['y'].to_numpy()[0]
    meta['X_STEP'], _, _, _, meta['Y_STEP'], *_ = dataset.attrs['transform']
    meta['DATA_TYPE'] = example_image['data_type'].values.item()
    meta['EPSG'] = example_image['epsg'].values.item()
    meta['X_UNIT'] = 'meters'
    meta['Y_UNIT'] = 'meters'
    meta['NoDataValue'] = example_image['nodata'].values.item()
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(meta['EPSG'])
    meta['UTM_ZONE'] = srs.GetName().split(' ')[-1]

    # add universal hyp3 metadata
    meta['PROCESSOR'] = 'hyp3'
    meta['ALOOKS'] = hyp3_meta['azimuth_looks']
    meta['RLOOKS'] = hyp3_meta['range_looks']
    meta['EARTH_RADIUS'] = np.mean(hyp3_meta['earth_radius_at_nadir'])
    meta['HEIGHT'] = np.mean(hyp3_meta['spacecraft_height'])
    meta['STARTING_RANGE'] = np.mean(hyp3_meta['slant_range_near'])
    meta['CENTER_LINE_UTC'] = np.mean(hyp3_meta['utc_time'])
    meta['HEADING'] = np.mean(hyp3_meta['heading']) % 360.0 - 360.0  # ensure negative value for the heading angle

    # add LAT/LON_REF1/2/3/4 based on whether satellite ascending or descending
    N = float(meta['Y_FIRST'])
    W = float(meta['X_FIRST'])
    S = N + float(meta['Y_STEP']) * int(meta['LENGTH'])
    E = W + float(meta['X_STEP']) * int(meta['WIDTH'])

    # convert UTM to lat/lon
    N, W = utm2latlon(meta['UTM_ZONE'], W, N)
    S, E = utm2latlon(meta['UTM_ZONE'], E, S)

    meta['ORBIT_DIRECTION'] = hyp3_meta['reference_orbit_direction'].upper()
    if meta['ORBIT_DIRECTION'] == 'ASCENDING':
        meta['LAT_REF1'] = str(S)
        meta['LAT_REF2'] = str(S)
        meta['LAT_REF3'] = str(N)
        meta['LAT_REF4'] = str(N)
        meta['LON_REF1'] = str(W)
        meta['LON_REF2'] = str(E)
        meta['LON_REF3'] = str(W)
        meta['LON_REF4'] = str(E)
    else:
        meta['LAT_REF1'] = str(N)
        meta['LAT_REF2'] = str(N)
        meta['LAT_REF3'] = str(S)
        meta['LAT_REF4'] = str(S)
        meta['LON_REF1'] = str(E)
        meta['LON_REF2'] = str(W)
        meta['LON_REF3'] = str(E)
        meta['LON_REF4'] = str(W)

    if hyp3_meta['reference_granule'][0].startswith('S1'):
        meta['PLATFORM'] = 'Sen'
        meta['ANTENNA_SIDE'] = -1
        meta['WAVELENGTH'] = SPEED_OF_LIGHT / SENTINEL1['carrier_frequency']
        meta['RANGE_PIXEL_SIZE'] = SENTINEL1['range_pixel_size'] * int(meta['RLOOKS'])
        meta['AZIMUTH_PIXEL_SIZE'] = SENTINEL1['azimuth_pixel_size'] * int(meta['ALOOKS'])
    else:
        raise NotImplementedError('Only Sentinel-1 data is currently supported')

    date1s = [dt.datetime.fromisoformat(x).strftime('%Y%m%d') for x in hyp3_meta['start_datetime']]
    date2s = [dt.datetime.fromisoformat(x).strftime('%Y%m%d') for x in hyp3_meta['end_datetime']]
    date12s = [f'{d1}_{d2}' for d1, d2 in zip(date1s, date2s)]

    perp_baseline = np.abs(hyp3_meta['baseline'])
    return meta, date12s, perp_baseline


def write_mintpy_ifgram_stack(
    outfile: str, dataset: xr.Dataset, metadata: dict, date12s: Iterable, perp_baselines: np.ndarray
):
    """Create a MintPy compatible interferogram stack and write it to a file.

    Args:
        outfile: output file path
        dataset: Xarray dataset of HyP3 InSAR products
        metadata: metadata dictionary
        date12s: list of date pairs
        perp_baselines: array of perpendicular baselines
    """
    stack_dataset_names = {'unw_phase': 'unwrapPhase', 'corr': 'coherence'}
    has_conncomp = 'conncomp' in list(dataset.coords['band'].to_numpy())
    if has_conncomp:
        stack_dataset_names['conncomp'] = 'connectComponent'
    dataset.attrs = {}

    new_dataset = xr.Dataset()
    for name in stack_dataset_names:
        new_name = stack_dataset_names[name]
        new_dataset[new_name] = dataset.sel(band=name).astype(np.float32)
        new_dataset[new_name].attrs['MODIFICATION_TIME'] = str(time.time())

    new_dataset = new_dataset.drop_vars(list(dataset.coords))
    new_dataset['bperp'] = perp_baselines

    date1 = np.array([d1.split('_')[0].encode('utf-8') for d1 in date12s])
    date2 = np.array([d2.split('_')[1].encode('utf-8') for d2 in date12s])
    dates = np.array((date1, date2)).astype(np.unicode_).transpose()
    new_dataset['date'] = (('date12', 'pair'), dates)

    for key, value in metadata.items():
        new_dataset.attrs[key] = str(value)
    new_dataset.to_netcdf(outfile, format='NETCDF4', mode='w')

    # FIXME this shouldn't be needed, but the call below results in dropIfgram
    # being read back in as an int, not a bool.
    # new_dataset['dropIfgram'] = np.ones(new_dataset['unwrapPhase'].shape[0], dtype=np.bool_)
    shape = (new_dataset['unwrapPhase'].shape[0],)
    with h5py.File(outfile, 'a') as f:
        f.create_dataset('dropIfgram', shape=shape, dtype=np.bool_)
        f['dropIfgram'][:] = True


def write_mintpy_geometry(outfile: str, dataset: xr.Dataset, metadata: dict) -> None:
    """Create a MintPy compatible geometry stack and write it to a file.

    Args:
        outfile: output file path
        dataset: Xarray dataset of HyP3 InSAR products
        metadata: metadata dictionary
    """
    first_product = dataset.isel(time=0)
    first_product.attrs = {}

    # Convert from hyp3/gamma to mintpy/isce2 convention
    incidence_angle = first_product.sel(band='lv_theta')
    incidence_angle = incidence_angle.where(incidence_angle == 0, np.nan)
    incidence_angle = 90 - (incidence_angle * 180 / np.pi)
    incidence_angle = incidence_angle.where(np.isnan(incidence_angle), 0)

    # Calculate Slant Range distance
    slant_range_distance = incidence_angle2slant_range_distance(
        metadata['HEIGHT'], metadata['EARTH_RADIUS'], incidence_angle
    )

    # Convert from hyp3/gamma to mintpy/isce2 convention
    azimuth_angle = first_product.sel(band='lv_phi')
    azimuth_angle = azimuth_angle.where(azimuth_angle == 0, np.nan)
    azimuth_angle = azimuth_angle * 180 / np.pi - 90  # hyp3/gamma to mintpy/isce2 convention
    azimuth_angle = wrap(azimuth_angle, wrap_range=[-180, 180])  # rewrap within -180 to 180
    azimuth_angle = azimuth_angle.where(np.isnan(azimuth_angle), 0)

    bands = {
        'height': first_product.sel(band='dem'),
        'incidenceAngle': incidence_angle,
        'slantRangeDistance': slant_range_distance,
        'azimuthAngle': azimuth_angle,
        'waterMask': first_product.sel(band='water_mask'),
    }
    new_dataset = xr.Dataset()
    for name in bands:
        dtype = np.bool_ if name == 'water_mask' else np.float32
        new_dataset[name] = bands[name].astype(dtype)
        new_dataset[name].attrs['MODIFICATION_TIME'] = str(time.time())

    new_dataset = new_dataset.drop_vars(list(dataset.coords))
    for key, value in metadata.items():
        new_dataset.attrs[key] = str(value)
    new_dataset.to_netcdf(outfile, format='NETCDF4', mode='w')


def create_xarray_dataset(
    stac_items: Iterable[pystac.Item],
    select_bands: Optional[Iterable[str]] = None,
    subset_geo: Optional[Iterable[float]] = None,
    subset_xy: Optional[Iterable[int]] = None,
    chunksize: Optional[str | dict] = '5 MB',
):
    """Create an Xarray dataset from a list of STAC items.

    Args:
        stac_items: list of STAC items
        select_bands: list of bands to select
        subset_geo: geographic subset as [W, E, S, N]
        subset_xy: index subset as [x1, x2, y1, y2]
        chunksize: chunk size for Dask in any format accepted by Dask

    Returns:
        Xarray dataset
    """
    # Not sure if stackstac is the best package to use. Could also use odc-stac as for example.
    dataset = stackstac.stack(stac_items, chunksize=chunksize, fill_value=0)

    if select_bands:
        dataset = dataset.sel(band=select_bands)

    if subset_geo and subset_xy:
        print('Both geographic and index subsets were provided. Using geographic subset method.')

    if subset_geo:
        dataset = dataset.sel(x=slice(subset_geo[0], subset_geo[1]), y=slice(subset_geo[3], subset_geo[2]))
    elif subset_xy:
        dataset = dataset.isel(x=slice(subset_xy[0], subset_xy[1]), y=slice(subset_xy[2], subset_xy[3]))

    return dataset


def create_mintpy_inputs(
    stac_collection_file: str,
    subset_geo: Optional[Iterable[float]] = None,
    subset_xy: Optional[Iterable[int]] = None,
    mintpy_dir: Optional[str] = None,
    chunksize: str = '15 MB',
    n_threads: int = 20,
):
    """Create MintPy compatible input files from a STAC collection.

    Args:
        stac_collection_file: path to the STAC collection file
        subset_geo: geographic subset as [W, E, S, N]
        subset_xy: index subset as [x1, x2, y1, y2]
        mintpy_dir: directory to create "input" dir in where the MintPy files will be saved
        chunksize: chunk size for Dask in any format accepted by Dask
        n_threads: number of threads to use for Dask
    """
    if mintpy_dir is None:
        mintpy_dir = Path.cwd()
    mintpy_dir = Path(mintpy_dir)

    collection = pystac.Collection.from_file(stac_collection_file)
    items = list(collection.get_all_items())

    dataset = create_xarray_dataset(items, subset_geo=subset_geo, subset_xy=subset_xy, chunksize=chunksize)

    meta, date12s, perp_baselines = get_metadata(dataset)

    input_dir = mintpy_dir / 'inputs'
    input_dir.mkdir(exist_ok=True, parents=True)

    msg = f'Downloading using a chunk size of {chunksize}'
    if n_threads > 1:
        msg += f' and {n_threads} threads'
        dask.config.set(scheduler='threads', num_workers=n_threads)
    print(msg)

    meta['FILE_TYPE'] = 'ifgramStack'
    ifg_outfile = input_dir / 'ifgramStack.h5'
    print('Creating interferogram stack...')
    write_mintpy_ifgram_stack(ifg_outfile, dataset, meta, date12s, perp_baselines)

    meta['FILE_TYPE'] = 'geometry'
    geom_outfile = input_dir / 'geometryGeo.h5'
    print('Creating geometry dataset...')
    write_mintpy_geometry(geom_outfile, dataset, meta)

    print('Done!')


if __name__ == '__main__':
    create_mintpy_inputs('./stac/collection.json', subset_geo=[3903739, 3992303, 403177, 498368])
