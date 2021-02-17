import responses

from hyp3_sdk import asf_search


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
    mock_response = {
        'results': [
            {'temporalBaseline': 12},
            {'temporalBaseline': -60},
            {'temporalBaseline': -12},
            {'temporalBaseline': -24},
        ]
    }
    responses.add(responses.GET, asf_search._BASELINE_API, json=mock_response)

    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_') == \
           [{'temporalBaseline': -12}, {'temporalBaseline': -24}]

    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_', max_neighbors=3) == \
           [{'temporalBaseline': -12}, {'temporalBaseline': -24}, {'temporalBaseline': -60}]

    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_', max_neighbors=100) == \
           [{'temporalBaseline': -12}, {'temporalBaseline': -24}, {'temporalBaseline': -60}]
