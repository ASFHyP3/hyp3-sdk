"""Tests for the stac module"""
from hyp3_sdk import stac


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
    """Test the GeoInfo class"""
    geo_info = stac.GeoInfo(
        transform=[1, 2, 3, 4, 5, 6],
        shape=[7, 8],
        epsg=9,
    )

    assert geo_info.bbox == [1, 46, 17, 4]
    assert geo_info.bbox_geojson == {
        'type': 'Polygon',
        'coordinates': [
            [
                [1, 6],
                [7, 6],
                [7, 4],
                [1, 4],
                [1, 6],
            ]
        ],
    }
    assert geo_info.proj_transform == [2, 3, 1, 6, 5, 4, 0, 0, 1]
