import pytest
from requests import Response
from requests.exceptions import HTTPError

from hyp3_sdk import exceptions


def test_hyp3_raise_for_status():
    response = Response()
    response.status_code = 400
    response._content = b'{ "detail" : "foo" }'

    with pytest.raises(exceptions.HyP3Error) as e:
        exceptions.hyp3_raise_for_status(response)
    assert 'foo' in str(e)

    response = Response()
    response.status_code = 500

    with pytest.raises(HTTPError):
        exceptions.hyp3_raise_for_status(response)

    response = Response()
    response.status_code = 200
    exceptions.hyp3_raise_for_status(response)


def test_search_raise_for_status():
    response = Response()
    response.status_code = 400
    response._content = b'{ "error" : { "report" : "bar"} }'

    with pytest.raises(exceptions.ASFSearchError) as e:
        exceptions.search_raise_for_status(response)
    assert 'bar' in str(e)

    response = Response()
    response.status_code = 500

    with pytest.raises(HTTPError):
        exceptions.search_raise_for_status(response)

    response = Response()
    response.status_code = 200
    exceptions.search_raise_for_status(response)
