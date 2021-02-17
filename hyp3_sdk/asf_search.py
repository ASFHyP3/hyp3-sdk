from typing import Iterable, List, Union

import requests

_BASELINE_API = 'https://api.daac.asf.alaska.edu/services/search/baseline'
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
    response.raise_for_status()

    metadata = [result for result in response.json()['results']
                if not result['productType'].startswith('METADATA_')]

    if isinstance(granules, str):
        return metadata[0]

    return metadata


def get_nearest_neighbors(granule: str, max_neighbors: int = 2,) -> List[dict]:
    """Get a granules nearest neighbors from a temporal stack (backwards in time)

    Args:
        granule: reference granule
        max_neighbors: maximum number of neighbors to return

    Returns:
        neighbors: a list of neighbors sorted by time
    """
    params = {
        'output': 'jsonlite',
        'master': granule,
    }
    response = requests.get(_BASELINE_API, params=params)
    response.raise_for_status()
    all_neighbors = response.json()['results']
    selected_neighbors = [n for n in all_neighbors if n['temporalBaseline'] < 0]
    selected_neighbors.sort(key=lambda k: k['temporalBaseline'], reverse=True)

    return selected_neighbors[:max_neighbors]
