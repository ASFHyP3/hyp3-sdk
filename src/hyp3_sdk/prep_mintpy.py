import datetime as dt
import time
from pathlib import Path

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


def incidence_angle2slant_range_distance(atr, inc_angle):
    """Calculate the corresponding slant range distance given an incidence angle

    Law of sines:
               r + H                   r               range_dist
       --------------------- = ----------------- = ------------------ = 2R
        sin(pi - inc_angle)     sin(look_angle)     sin(range_angle)

    where range_angle = inc_angle - look_angle
          R is the radius of the circumcircle.

    link: http://www.ambrsoft.com/TrigoCalc/Triangle/BasicLaw/BasicTriangle.htm

    Parameters: atr         - dict, metadata including the following items:
                                  EARTH_RADIUS
                                  HEIGHT
                inc_angle   - float / np.ndarray, incidence angle in degree
    Returns:    slant_range - float, slant range distance
    """
    inc_angle = inc_angle / 180 * np.pi
    r = float(atr['EARTH_RADIUS'])
    H = float(atr['HEIGHT'])

    # calculate 2R based on the law of sines
    R2 = (r + H) / np.sin(np.pi - inc_angle)

    look_angle = np.arcsin(r / R2)
    range_angle = inc_angle - look_angle
    range_dist = R2 * np.sin(range_angle)

    return range_dist


def utm2latlon(meta, easting, northing):
    """Convert UTM easting/northing in meters to lat/lon in degrees.

    Parameters: meta     - dict, mintpy attributes that includes:
                           UTM_ZONE
                easting  - scalar or 1/2D np.ndarray, UTM    coordinates in x direction
                northing - scalar or 1/2D np.ndarray, UTM    coordinates in y direction
    Returns:    lat      - scalar or 1/2D np.ndarray, WGS 84 coordinates in y direction
                lon      - scalar or 1/2D np.ndarray, WGS 84 coordinates in x direction
    """

    zone_num = int(meta['UTM_ZONE'][:-1])
    northern = meta['UTM_ZONE'][-1].upper() == 'N'
    # set 'strict=False' to allow coordinates outside the range of a typical single UTM zone,
    # which can be common for large area analysis, e.g. the Norwegian mapping authority
    # publishes a height data in UTM zone 33 coordinates for the whole country, even though
    # most of it is technically outside zone 33.
    lat, lon = utm.to_latlon(easting, northing, zone_num, northern=northern, strict=False)
    return lat, lon


def wrap(data, wrap_range=[-1.0 * np.pi, np.pi]):
    """Wrap data into a range.
    Parameters: data_in    : np.array, array to be wrapped
                wrap_range : list of 2 float, range to be wrapped into
    Returns:    data       : np.array, data after wrapping
    """
    w0, w1 = wrap_range
    data = w0 + np.mod(data - w0, w1 - w0)
    return data


def get_metadata(dataset):
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
    N, W = utm2latlon(meta, W, N)
    S, E = utm2latlon(meta, E, S)

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


def write_mintpy_ifgram_stack(outfile, dataset, metadata, date12s, perp_baselines):
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


def write_mintpy_geometry(outfile, dataset, metadata):
    first_product = dataset.isel(time=0)
    first_product.attrs = {}

    # Convert from hyp3/gamma to mintpy/isce2 convention
    incidence_angle = first_product.sel(band='lv_theta')
    incidence_angle = incidence_angle.where(incidence_angle == 0, np.nan)
    incidence_angle = 90 - (incidence_angle * 180 / np.pi)
    incidence_angle = incidence_angle.where(np.isnan(incidence_angle), 0)

    # Calculate Slant Range distance
    slant_range_distance = incidence_angle2slant_range_distance(metadata, incidence_angle)

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


def create_xarray_dataset(stac_items, select_bands=None, subset_geo=None, subset_yx=None, chunksize='5 MB'):
    dataset = stackstac.stack(stac_items, chunksize=chunksize, fill_value=0)

    if select_bands:
        dataset = dataset.sel(band=select_bands)

    if subset_geo and subset_yx:
        print('Both geographic and index subsets were provided. Using geographic subset method.')

    if subset_geo:
        dataset = dataset.sel(y=slice(subset_geo[1], subset_geo[0]), x=slice(subset_geo[2], subset_geo[3]))
    elif subset_yx:
        dataset = dataset.isel(y=slice(subset_yx[0], subset_yx[1]), x=slice(subset_yx[2], subset_yx[3]))

    return dataset


def create_mintpy_inputs(
    stac_file,
    subset_yx=None,
    subset_geo=None,
    compression=None,
    mintpy_dir=None,
    chunksize='5 MB',
):
    if mintpy_dir is None:
        mintpy_dir = Path.cwd()

    collection = pystac.Collection.from_file(stac_file)
    items = list(collection.get_all_items())

    dataset = create_xarray_dataset(items, subset_geo=subset_geo, subset_yx=subset_yx, chunksize=chunksize)

    meta, date12s, perp_baselines = get_metadata(dataset)

    input_dir = mintpy_dir / 'inputs'
    input_dir.mkdir(exist_ok=True, parents=True)

    meta['FILE_TYPE'] = 'ifgramStack'
    ifg_outfile = input_dir / f'{meta["FILE_TYPE"]}.h5'
    write_mintpy_ifgram_stack(ifg_outfile, dataset, meta, date12s, perp_baselines)

    meta['FILE_TYPE'] = 'geometry'
    geom_outfile = input_dir / f'{meta["FILE_TYPE"]}.h5'
    write_mintpy_geometry(geom_outfile, dataset, meta)


if __name__ == '__main__':
    create_mintpy_inputs('./stac/collection.json', subset_geo=[3903739, 3992303, 403177, 498368])
