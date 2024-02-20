"""Tests for the stac module"""
from datetime import datetime

import numpy as np
import pytest
import tifffile
from hyp3_sdk import Job, stac


def test_parameter_file(tmp_path):
    """Test the ParameterFile class"""
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

    assert str(param_file).startswith('Reference Granule: foo\n')
    assert str(param_file).endswith('Water mask: yes\n')

    param_file.write(tmp_path / 'test.txt')
    assert (tmp_path / 'test.txt').read_text() == str(param_file)
    loaded_param_file = stac.ParameterFile.read(tmp_path / 'test.txt')
    assert loaded_param_file == param_file


def test_geoinfo():
    geo_info = stac.GeoInfo(
        transform=[10, 1, 0, 400, 0, -2],
        shape=[100, 200],
        epsg=123456,
    )
    assert geo_info.bbox == [10, 200, 210, 400]
    assert geo_info.bbox_geojson == {
        'type': 'Polygon',
        'coordinates': [
            [
                [10, 200],
                [210, 200],
                [210, 400],
                [10, 400],
                [10, 200],
            ]
        ],
    }
    assert geo_info.proj_transform == [1, 0, 10, 0, -2, 400, 0, 0, 1]


def test_get_epsg():
    test_geo_key_list = [9999, 0, 1, 5555, 3072, 0, 1, 4326]
    assert stac.get_epsg(test_geo_key_list) == 4326

    test_geo_key_list = [9999, 0, 1, 4326, 3071, 0, 1, 4326]
    with pytest.raises(ValueError, match='No .* EPSG .*'):
        stac.get_epsg(test_geo_key_list)


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
    tifffile.imsave(
        file_path,
        image_data,
        extratags=extra_tags,
    )
    return


def test_get_geotiff_info_nogdal(tmp_path):
    tmp_file = tmp_path / 'test.tif'
    create_temp_geotiff(tmp_file)
    geo_info = stac.get_geotiff_info_nogdal(str(tmp_file))
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
    job4 = Job(job_type='INSAR_ISCE_BURST', job_id='foo', request_time=datetime.now(), status_code='SUCCEEDED', user_id='me')
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
