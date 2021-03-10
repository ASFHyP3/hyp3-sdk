import pytest
import responses

from hyp3_sdk import asf_search
from hyp3_sdk.exceptions import ASFSearchError


@responses.activate
def test_get_metadata_string():
    responses.add(responses.POST, asf_search._SEARCH_API,
                  json={'results': [
                      {'productType': 'METADATA_SLC'},
                      {'productType': 'SLC'},
                  ]})
    assert asf_search.get_metadata('S1B_IW_SLC_') == {'productType': 'SLC'}


@responses.activate
def test_get_metadata_list():
    mock_response = {
        'results': [
            {'productType': 'GRD_HD'},
            {'productType': 'METADATA_GRD'},
            {'productType': 'METADATA_SLC'},
            {'productType': 'SLC'},
        ]
    }
    responses.add(responses.POST, asf_search._SEARCH_API, json=mock_response)

    assert asf_search.get_metadata(['S1B_IW_SLC_', 'S1B_IW_SLC_']) == \
           [{'productType': 'GRD_HD'}, {'productType': 'SLC'}]


@responses.activate
def test_get_nearest_neighbor():
    reference = 'S1A_IW_SLC__1SDV_20161106T002750_20161106T002817_013814_016338_19F7'

    reference_query = f'{asf_search._SEARCH_API}' \
                      '?output=json' \
                      '&platform=S1' \
                      f'&granule_list={reference}'
    reference_response = [[
        {
            'centerLon': '0.0',
            'centerLat': '1.0',
            'startTime': '2016-11-06T00:27:50.000000',
            'beamMode': 'IW',
            'flightDirection': 'DESCENDING',
            'processingLevel': 'SLC',
            'relativeOrbit': '1',
            'polarization': 'VV+VH',
            'lookDirection': 'R',
        },
        {
            'centerLon': 'x',
            'centerLat': 'x',
            'startTime': 'x',
            'beamMode': 'x',
            'flightDirection': 'x',
            'processingLevel': 'METADATA_SLC',
            'relativeOrbit': 'x',
            'polarization': 'x',
            'lookDirection': 'x',
        },
    ]]
    responses.add(responses.POST, reference_query, json=reference_response)

    stack_query = f'{asf_search._SEARCH_API}' \
                  '?output=jsonlite' \
                  '&platform=S1' \
                  '&intersectsWith=POINT+(0.0+1.0)' \
                  '&end=2016-11-06T00:27:50.000000' \
                  '&beamMode=IW' \
                  '&flightDirection=DESCENDING' \
                  '&processingLevel=SLC' \
                  '&relativeOrbit=1' \
                  '&polarization=VV%2CVV%2BVH' \
                  '&lookDirection=R'
    stack_response = {
        'results': [
            {'startTime': 1},
            {'startTime': 5},
            {'startTime': 4},
            {'startTime': 2},
            {'startTime': 3},
        ]
    }
    responses.add(responses.POST, stack_query, json=stack_response)

    assert asf_search.get_nearest_neighbors(reference) == \
           [{'startTime': 4}, {'startTime': 3}]
    assert asf_search.get_nearest_neighbors(reference, max_neighbors=3) == \
           [{'startTime': 4}, {'startTime': 3}, {'startTime': 2}]


@responses.activate
def test_get_nearest_neighbors_no_reference():
    responses.add(responses.POST, asf_search._SEARCH_API, json=[[]])
    with pytest.raises(ASFSearchError) as e:
        asf_search.get_nearest_neighbors('foo')
    assert 'foo' in str(e)


@responses.activate
def test_get_nearest_neighbors_no_reference_only_metadata():
    responses.add(responses.POST, asf_search._SEARCH_API, json=[[{'processingLevel': 'METADATA_SLC'}]])
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
