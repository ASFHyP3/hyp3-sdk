import pytest
from requests import Response
from requests.exceptions import HTTPError

from hyp3_sdk import exceptions


def test_raise_for_hyp3_status():
    response = Response()
    response.status_code = 400
    response._content = b'{ "detail" : "foo" }'

    with pytest.raises(exceptions.HyP3Error) as e:
        exceptions.raise_for_hyp3_status(response)
    assert 'foo' in str(e)

    response = Response()
    response.status_code = 500

    with pytest.raises(HTTPError):
        exceptions.raise_for_hyp3_status(response)

    response = Response()
    response.status_code = 200
    exceptions.raise_for_hyp3_status(response)


def test_raise_for_search_status():
    response = Response()
    response.status_code = 400
    response._content = b'{ "error" : { "report" : "bar"} }'

    with pytest.raises(exceptions.ASFSearchError) as e:
        exceptions.raise_for_search_status(response)
    assert 'bar' in str(e)

    response = Response()
    response.status_code = 500

    with pytest.raises(HTTPError):
        exceptions.raise_for_search_status(response)

    response = Response()
    response.status_code = 200
    exceptions.raise_for_search_status(response)