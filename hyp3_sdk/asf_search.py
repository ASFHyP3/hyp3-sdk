import warnings
from typing import Iterable, List, Union

import requests
from shapely.geometry import shape

from hyp3_sdk.exceptions import ASFSearchError, _raise_for_search_status

warnings.warn('\nhyp3_sdk.asf_search is depreciated and functionality is '
              'being moved to the asf_search Package available on conda-forge and PyPI. '
              'See: https://github.com/asfadmin/Discovery-asf_search', FutureWarning)

_SEARCH_API = 'https://api.daac.asf.alaska.edu/services/search/param'


def get_metadata(granules: Union[str, Iterable[str]]) -> Union[dict, List[dict]]:
    """Get the metadata for a granule or list of granules

    Args:
        granules: granule(s) to lookup

    Returns:
        metadata: GeoJSON Feature or FeatureCollection of the requested granule(s)
    """
    warnings.warn('hyp3_sdk.asf_search.get_metadata is depreciated. We recommend using asf_search.granule_search '
                  'instead. See: https://github.com/asfadmin/Discovery-asf_search#usage', FutureWarning)

    if isinstance(granules, str):
        granule_list = granules
    else:
        granule_list = ','.join(granules)

    params = {
        'output': 'geojson',  # preferred by DISCOVERY-asf_search
        'granule_list': granule_list,
    }
    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)

    scenes = [result for result in response.json()['features']
              if not result['properties']['processingLevel'].startswith('METADATA_')]
    if isinstance(granules, str):
        return scenes[0]

    return {'features': scenes, 'type': 'FeatureCollection'}


def get_nearest_neighbors(granule: str, max_neighbors: int = 2,) -> dict:
    """Get a Sentinel-1 granule's nearest neighbors from a temporal stack (backwards in time)

    Args:
        granule: reference granule
        max_neighbors: maximum number of neighbors to return

    Returns:
        neighbors: GeoJSON FeatureCollection with a list of features for each neighbor, sorted by time
    """
    params = {
        'output': 'geojson',  # preferred by DISCOVERY-asf_search
        'platform': 'S1',
        'granule_list': granule,
    }
    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)
    references = [r for r in response.json()['features']
                  if not r['properties']['processingLevel'].startswith('METADATA_')]
    if not references:
        raise ASFSearchError(f'Reference Sentinel-1 granule {granule} could not be found')
    reference = references[0]
    reference_center_wkt = shape(reference['geometry']).centroid.wkt

    params = {
        'output': 'geojson',  # preferred by DISCOVERY-asf_search
        'platform': 'S1',
        'intersectsWith': reference_center_wkt,
        'end': reference['properties']['startTime'],  # includes reference scene
        'beamMode': reference['properties']['beamModeType'],
        'flightDirection': reference['properties']['flightDirection'],
        'processingLevel': reference['properties']['processingLevel'],
        'relativeOrbit': reference['properties']['pathNumber'],
        'polarization': _get_matching_polarizations(reference['properties']['polarization']),
    }

    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)

    neighbors = sorted(response.json()['features'], key=lambda x: x['properties']['startTime'], reverse=True)
    search_results = {'features': neighbors[1:max_neighbors+1], 'type': 'FeatureCollection'}
    return search_results


def _get_matching_polarizations(input_polarization: str):
    if input_polarization in ('VV', 'VV+VH'):
        return 'VV,VV+VH'
    if input_polarization in ('HH', 'HH+HV'):
        return 'HH,HH+HV'
    return input_polarization
