import warnings
from typing import Iterable, List, Union

import requests

from hyp3_sdk.exceptions import ASFSearchError, _raise_for_search_status

warnings.warn('\nhyp3_sdk.asf_search is deprecated and functionality has been '
              'superseded by the `asf_search` package available on conda-forge and PyPI. '
              'See: https://github.com/asfadmin/Discovery-asf_search', FutureWarning)

_SEARCH_API = 'https://api.daac.asf.alaska.edu/services/search/param'


def get_metadata(granules: Union[str, Iterable[str]]) -> Union[dict, List[dict]]:
    """Get the metadata for a granule or list of granules

    Args:
        granules: granule(s) to lookup metadata for

    Returns:
        metadata: metadata for the granule(s)
    """
    if isinstance(granules, str):
        granule_list = granules
    else:
        granule_list = ','.join(granules)

    params = {
        'output': 'jsonlite',
        'granule_list': granule_list,
    }
    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)

    metadata = [result for result in response.json()['results']
                if not result['productType'].startswith('METADATA_')]

    if isinstance(granules, str):
        return metadata[0]

    return metadata


def get_nearest_neighbors(granule: str, max_neighbors: int = 2,) -> List[dict]:
    """Get a Sentinel-1 granule's nearest neighbors from a temporal stack (backwards in time)

    Args:
        granule: reference granule
        max_neighbors: maximum number of neighbors to return

    Returns:
        neighbors: a list of neighbors sorted by time
    """
    params = {
        'output': 'json',  # jsonlite doesn't include centerLat/centerLon
        'platform': 'S1',
        'granule_list': granule,
    }
    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)
    references = [r for r in response.json()[0] if not r['processingLevel'].startswith('METADATA_')]
    if not references:
        raise ASFSearchError(f'Reference Sentinel-1 granule {granule} could not be found')
    reference = references[0]

    params = {
        'output': 'jsonlite',
        'platform': 'S1',
        'intersectsWith': f'POINT ({reference["centerLon"]} {reference["centerLat"]})',
        'end': reference['startTime'],  # includes reference scene
        'beamMode': reference['beamMode'],
        'flightDirection': reference['flightDirection'],
        'processingLevel': reference['processingLevel'],
        'relativeOrbit': reference['relativeOrbit'],
        'polarization': _get_matching_polarizations(reference['polarization']),
        'lookDirection': reference['lookDirection'],
    }
    response = requests.post(_SEARCH_API, params=params)
    _raise_for_search_status(response)
    neighbors = sorted(response.json()['results'], key=lambda x: x['startTime'], reverse=True)
    return neighbors[1:max_neighbors+1]


def _get_matching_polarizations(input_polarization: str):
    if input_polarization in ('VV', 'VV+VH'):
        return 'VV,VV+VH'
    if input_polarization in ('HH', 'HH+HV'):
        return 'HH,HH+HV'
    return input_polarization
