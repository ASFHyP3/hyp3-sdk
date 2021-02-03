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
    responses.add(responses.POST, asf_search._SEARCH_API,
                  json={'results': [
                      {'productType': 'SLC'},
                      {'productType': 'METADATA_SLC'},
                      {'productType': 'METADATA_SLC'},
                      {'productType': 'SLC'},
                  ]})
    assert asf_search.get_metadata(['S1B_IW_SLC_', 'S1B_IW_SLC_']) == [{'productType': 'SLC'}, {'productType': 'SLC'}]


@responses.activate
def test_get_nearest_neighbor():
    responses.add(responses.GET, asf_search._BASLINE_API,
                  json={'results': [
                      {'temporalBaseline': 12},
                      {'temporalBaseline': -60},
                      {'temporalBaseline': -12},
                      {'temporalBaseline': -24},
                  ]})

    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_') == [{'temporalBaseline': -12}, {'temporalBaseline': -24}]
    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_', total=3) == \
           [{'temporalBaseline': -12}, {'temporalBaseline': -24}, {'temporalBaseline': -60}]
    assert asf_search.get_nearest_neighbors('S1B_IW_SLC_', total=100) == \
           [{'temporalBaseline': -12}, {'temporalBaseline': -24}, {'temporalBaseline': -60}]
