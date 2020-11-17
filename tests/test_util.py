import responses

from hyp3_sdk.util import download_file


@responses.activate
def test_download_file(tmp_path):
    responses.add(responses.GET, 'https://foo.com/file', body='foobar')
    result_path = download_file('https://foo.com/file', tmp_path / 'file')
    assert result_path == (tmp_path / 'file')
    assert result_path.read_text() == 'foobar'
