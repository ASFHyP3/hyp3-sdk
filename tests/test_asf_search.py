import pytest
import responses

from hyp3_sdk import asf_search
from hyp3_sdk.exceptions import ASFSearchError


@responses.activate
def test_get_metadata_string():
    responses.add(responses.POST, asf_search._SEARCH_API,
                  json={'features': [
                      {'properties': {'processingLevel': 'METADATA_SLC'}},
                      {'properties': {'processingLevel': 'SLC'}},
                  ]})
    assert asf_search.get_metadata('S1B_IW_SLC_') == {'properties': {'processingLevel': 'SLC'}}


@responses.activate
def test_get_metadata_list():
    mock_response = {
        'features': [
            {'properties': {'processingLevel': 'GRD_HD'}},
            {'properties': {'processingLevel': 'METADATA_GRD'}},
            {'properties': {'processingLevel': 'METADATA_SLC'}},
            {'properties': {'processingLevel': 'SLC'}},
        ]
    }
    responses.add(responses.POST, asf_search._SEARCH_API, json=mock_response)

    assert asf_search.get_metadata(['S1B_IW_SLC_', 'S1B_IW_SLC_']) == {
        'type': 'FeatureCollection',
        'features': [{'properties': {'processingLevel': 'GRD_HD'}}, {'properties': {'processingLevel': 'SLC'}}]
    }


@responses.activate
def test_get_nearest_neighbor():
    reference = 'S1A_IW_SLC__1SDV_20161106T002750_20161106T002817_013814_016338_19F7'

    reference_query = f'{asf_search._SEARCH_API}' \
                      '?output=geojson' \
                      '&platform=Sentinel-1' \
                      f'&granule_list={reference}'

    reference_response = {'features': [
        {
            'geometry': {
                'coordinates': [[[80.848305, 25.82291], [81.164093, 27.446077], [83.678406, 27.034683],
                                 [83.32576, 25.408642], [80.848305, 25.82291]]],
                'type': 'Polygon'
            },
            'properties': {'beamModeType': 'IW',
                           'flightDirection': 'DESCENDING',
                           'pathNumber': '92',
                           'polarization': 'VV+VH',
                           'processingLevel': 'SLC',
                           'startTime': '2016-11-06T00:27:50.000000',
                           },
            'type': 'Feature'
        }
    ], 'type': 'FeatureCollection'}

    responses.add(responses.POST, reference_query, json=reference_response)

    stack_query = f'{asf_search._SEARCH_API}' \
                  '?output=geojson' \
                  '&platform=Sentinel-1' \
                  '&intersectsWith=POINT+%2882.2556430369368+26.42979676529672%29' \
                  '&end=2016-11-06T00:27:50.000000' \
                  '&beamMode=IW' \
                  '&flightDirection=DESCENDING' \
                  '&processingLevel=SLC' \
                  '&relativeOrbit=92' \
                  '&polarization=VV%2CVV%2BVH'
    stack_response = {
        'features': [
            {'properties': {'startTime': 1}},
            {'properties': {'startTime': 5}},
            {'properties': {'startTime': 4}},
            {'properties': {'startTime': 2}},
            {'properties': {'startTime': 3}},
        ]
    }
    responses.add(responses.POST, stack_query, json=stack_response)

    assert asf_search.get_nearest_neighbors(reference) == {
        'features': [{'properties': {'startTime': 4}}, {'properties': {'startTime': 3}}],
        'type': 'FeatureCollection'
    }
    assert asf_search.get_nearest_neighbors(reference, max_neighbors=3) == {
        'features': [{'properties': {'startTime': 4}}, {'properties': {'startTime': 3}},
                     {'properties': {'startTime': 2}}],
        'type': 'FeatureCollection'
    }


@responses.activate
def test_get_nearest_neighbors_no_reference():
    responses.add(responses.POST, asf_search._SEARCH_API, json={'features': []})
    with pytest.raises(ASFSearchError) as e:
        asf_search.get_nearest_neighbors('foo')
    assert 'foo' in str(e)


@responses.activate
def test_get_nearest_neighbors_no_reference_only_metadata():
    responses.add(responses.POST, asf_search._SEARCH_API, json={
        'features': [{'properties': {'processingLevel': 'METADATA_GRD'}}]
    })
    with pytest.raises(ASFSearchError) as e:
        asf_search.get_nearest_neighbors('foo')
    assert 'foo' in str(e)


def test_get_matching_polarizations():
    assert asf_search._get_matching_polarizations('VV') == 'VV,VV+VH'
    assert asf_search._get_matching_polarizations('VV+VH') == 'VV,VV+VH'
    assert asf_search._get_matching_polarizations('HH') == 'HH,HH+HV'
    assert asf_search._get_matching_polarizations('HH+HV') == 'HH,HH+HV'
    assert asf_search._get_matching_polarizations('HH') == 'HH,HH+HV'
    assert asf_search._get_matching_polarizations('Dual VV') == 'Dual VV'
    assert asf_search._get_matching_polarizations('Dual VH') == 'Dual VH'
    assert asf_search._get_matching_polarizations('Dual HH') == 'Dual HH'
    assert asf_search._get_matching_polarizations('Dual HV') == 'Dual HV'
