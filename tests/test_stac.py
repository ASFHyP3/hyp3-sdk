"""Tests for the stac module"""
from copy import deepcopy
from datetime import datetime, timezone

import numpy as np
import pytest
import tifffile

from hyp3_sdk import Job
from hyp3_sdk.stac import stac


@pytest.fixture
def param_file():
    param_file = stac.ParameterFile(
        reference_granule='foo',
        secondary_granule='bar',
        reference_orbit_direction='ASCENDING',
        reference_orbit_number=123,
        secondary_orbit_direction='DESCENDING',
        secondary_orbit_number=124,
        baseline=100.0,
        utc_time=1546344000.0,
        heading=0.0,
        spacecraft_height=700000.0,
        earth_radius_at_nadir=6371000.0,
        slant_range_near=800000.0,
        slant_range_center=850000.0,
        slant_range_far=900000.0,
        range_looks=5,
        azimuth_looks=5,
        insar_phase_filter=True,
        phase_filter_parameter=0.2,
        range_bandpass_filter=True,
        azimuth_bandpass_filter=True,
        dem_source='baz',
        dem_resolution=30,
        unwrapping_type='SNAPHU',
        speckle_filter=True,
        water_mask=True,
    )
    return param_file


@pytest.fixture
def geo_info():
    return stac.GeoInfo(transform=[677962, 1, 0, 4096742, 0, -1], shape=[108630, 92459], epsg=32610)


def test_parameter_file(tmp_path, param_file):
    """Test the ParameterFile class"""
    assert str(param_file).startswith('Reference Granule: foo\n')
    assert str(param_file).endswith('Water mask: yes\n')

    param_file.write(tmp_path / 'test.txt')
    assert (tmp_path / 'test.txt').read_text() == str(param_file)
    loaded_param_file = stac.ParameterFile.read(tmp_path / 'test.txt')
    assert loaded_param_file == param_file


def test_geoinfo(geo_info):
    assert np.all(np.round(geo_info.bbox, 4) == np.round([-121, 36, -120, 37], 4))
    assert geo_info.bbox_geojson['type'] == 'Polygon'
    assert len(geo_info.bbox_geojson['coordinates'][0]) == 5
    assert geo_info.proj_transform == [1, 0, 677962, 0, -1, 4096742, 0, 0, 1]


def test__get_epsg():
    test_geo_key_list = [9999, 0, 1, 5555, 3072, 0, 1, 4326]
    assert stac._get_epsg(test_geo_key_list) == 4326

    test_geo_key_list = [9999, 0, 1, 4326, 3071, 0, 1, 4326]
    with pytest.raises(ValueError, match='No .* EPSG .*'):
        stac._get_epsg(test_geo_key_list)


def create_temp_geotiff(file_path):
    width, length = 100, 200
    pixel_x, pixel_y = 1, 2
    origin_x, origin_y = 10, 20
    image_data = np.zeros((length, width), dtype=np.uint16)

    tags = {
        'ModelPixelScaleTag': [33550, 'i', 3, (pixel_x, pixel_y, 0)],
        'ModelTiepointTag': [33922, 'i', 6, (0, 0, 0, origin_x, origin_y, 0)],
        'GeoKeyDirectoryTag': [34735, 'i', 4, (3072, 0, 1, 4326)],
    }
    extra_tags = [tags[key] for key in tags]
    tifffile.imwrite(
        file_path,
        image_data,
        extratags=extra_tags,
    )
    return


def test__get_geotiff_info_nogdal(tmp_path):
    tmp_file = tmp_path / 'test.tif'
    create_temp_geotiff(tmp_file)
    geo_info = stac._get_geotiff_info_nogdal(str(tmp_file))
    assert geo_info.transform == [10, 1, 0, 20, 0, -2]
    assert geo_info.shape == (200, 100)
    assert geo_info.epsg == 4326


def test_get_overall_bbox():
    boxes = [[0, 2, 3, 4], [5, 0, 10, 8], [1, 6, 7, 11]]
    assert stac.get_overall_bbox(boxes) == [0, 0, 10, 11]


def test_validate_stac():
    job1 = Job(
        job_type='INSAR_GAMMA',
        job_id='foo',
        request_time=datetime.now(),
        status_code='SUCCEEDED',
        user_id='me',
        job_parameters={'reference_granule': 'foo', 'secondary_granule': 'bar'},
    )
    job2 = Job(
        job_type='INSAR_GAMMA',
        job_id='foo',
        request_time=datetime.now(),
        status_code='SUCCEEDED',
        user_id='me',
        job_parameters={'reference_granule': 'foo', 'secondary_granule': 'baz'},
    )
    job3 = Job(job_type='INSAR_GAMMA', job_id='foo', request_time=datetime.now(), status_code='PENDING', user_id='me')
    job4 = Job(
        job_type='INSAR_ISCE_BURST', job_id='foo', request_time=datetime.now(), status_code='SUCCEEDED', user_id='me'
    )
    job5 = Job(job_type='AUTORIFT', job_id='foo', request_time=datetime.now(), status_code='SUCCEEDED', user_id='me')

    with pytest.raises(ValueError, match='Not all .* succeeded .*'):
        stac.validate_stack([job1, job3])

    with pytest.raises(ValueError, match='Not all.*job type.*'):
        stac.validate_stack([job1, job4])

    with pytest.raises(ValueError, match='Not all .* parameters'):
        stac.validate_stack([job1, job2])

    with pytest.raises(NotImplementedError, match='Job type .* not supported.*'):
        stac.validate_stack([job5])

    stac.validate_stack([job1, job1])


def test__create_insar_stac_item(param_file, geo_info):
    job_gamma = Job(
        job_type='INSAR_GAMMA',
        job_id='my_job_id',
        request_time=datetime.now(),
        status_code='SUCCEEDED',
        user_id='me',
        files=[{'url': 'https://example.com/my_job_id.zip'}],
    )
    gamma_param_file = deepcopy(param_file)
    gamma_param_file.reference_granule = '0_1_2_3_4_20190101T000000'
    gamma_param_file.secondary_granule = '0_1_2_3_4_20190102T000000'
    item = stac._create_insar_stac_item(job_gamma, geo_info, gamma_param_file)
    item.validate()
    assert item.id == 'my_job_id'
    assert item.datetime == datetime(2019, 1, 1, 12, 0, 0).replace(tzinfo=timezone.utc)
    assert np.all(np.round(item.bbox, 4) == np.round([-121, 36, -120, 37], 4))
    assert item.properties['sar:product_type'] == 'INSAR_GAMMA'
    assert item.properties['sar:polarizations'] == ['VV']
    assert item.properties['hyp3:start_datetime'] == '2019-01-01T00:00:00+00:00'
    assert item.properties['hyp3:end_datetime'] == '2019-01-02T00:00:00+00:00'
    assert item.properties['hyp3:reference_granule'] == '0_1_2_3_4_20190101T000000'
    assert item.properties['hyp3:secondary_granule'] == '0_1_2_3_4_20190102T000000'
    assert item.assets['unw_phase'].href == 'https://example.com/my_job_id_unw_phase.tif'

    job_isce = Job(
        job_type='INSAR_ISCE_BURST',
        job_id='my_job_id',
        request_time=datetime.now(),
        status_code='SUCCEEDED',
        user_id='me',
        files=[{'url': 'https://example.com/my_job_id.zip'}],
    )
    isce_param_file = deepcopy(param_file)
    isce_param_file.reference_granule = '0_1_2_20190101T000000_VH'
    isce_param_file.secondary_granule = '0_1_2_20190102T000000_VH'
    item = stac._create_insar_stac_item(job_isce, geo_info, isce_param_file)
    item.validate()
    # only testing the new properties
    assert item.properties['sar:product_type'] == 'INSAR_ISCE_BURST'
    assert item.properties['sar:polarizations'] == ['VH']
    assert item.properties['hyp3:start_datetime'] == '2019-01-01T00:00:00+00:00'
    assert item.properties['hyp3:end_datetime'] == '2019-01-02T00:00:00+00:00'


def test__create_rtc_stac_item(geo_info):
    job = Job(
        job_type='RTC_GAMMA',
        job_id='my_job_20190101T000000',
        request_time=datetime.now(),
        status_code='SUCCEEDED',
        user_id='me',
        files=[{'url': 'https://example.com/my_job_20190101T000000.zip'}],
    )
    available_polarizations = ['VV', 'VH']
    item = stac._create_rtc_stac_item(job, geo_info, available_polarizations)
    item.validate()
    assert item.id == 'my_job_20190101T000000'
    assert item.datetime == datetime(2019, 1, 1, 0, 0, 0).replace(tzinfo=timezone.utc)
    assert np.all(np.round(item.bbox, 4) == np.round([-121, 36, -120, 37], 4))
    assert item.properties['sar:product_type'] == 'RTC_GAMMA'
    assert item.properties['sar:polarizations'] == ['VV', 'VH']
    assert item.assets['VV'].href == 'https://example.com/my_job_20190101T000000_VV.tif'


def test__create_item(geo_info):
    base_url = 'https://example.com/my_job_id.zip'
    start_time = datetime(2019, 1, 1, 0, 0, 0).replace(tzinfo=timezone.utc)
    product_types = ['unw_phase', 'corr']
    extra_properties = {'foo': 'bar'}
    item = stac._create_item(base_url, start_time, geo_info, product_types, extra_properties)
    assert item.id == 'my_job_id'
    assert item.datetime == start_time
    assert np.all(np.round(item.bbox, 4) == np.round([-121, 36, -120, 37], 4))
    assert item.properties['foo'] == 'bar'
    assert item.properties['sar:instrument_mode'] == 'IW'
    assert item.properties['sar:frequency_band'] == 'C'
    assert item.assets['unw_phase'].href == 'https://example.com/my_job_id_unw_phase.tif'
    assert item.assets['corr'].href == 'https://example.com/my_job_id_corr.tif'
