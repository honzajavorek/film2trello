from pathlib import Path

import responses
import pytest

import film2trello


@pytest.mark.parametrize('username,expected', [
    (None, None),
    ('', None),
    ('None', None),
    ('honzajavorek', 'honzajavorek'),
])
def test_parse_username(username, expected):
    assert film2trello.parse_username(username) == expected


def sanitize_exception():
    film2trello.sanitize_exception(f'''
        This is my token: {film2trello.TRELLO_TOKEN}
        And this is my key: {film2trello.TRELLO_KEY}
    ''') == '''
        This is my token: <TRELLO_TOKEN>
        And this is my key: <TRELLO_KEY>
    '''


def test_compress_javascript():
    film2trello.compress_javascript('''
        (function() {
          window.alert('Hello!');
          console.log('Hello!');
        })()
    ''') == "(function() { window.alert('Hello!'); console.log('Hello!'); })()"


@responses.activate
def test_get_film_url():
    url = film2trello.get_film_url('https://www.csfd.cz/film/988751-smolny-pich-aneb-pitomy-porno/prehled/')

    assert url == 'https://www.csfd.cz/film/988751/'
    assert len(responses.calls) == 0


@responses.activate
def test_get_film_url_kvifftv():
    responses.add(responses.GET,
                  'https://kviff.tv/katalog/smolny-pich-aneb-pitomy-porno',
                  body=(Path(__file__).parent / 'kvifftv.html').read_bytes(),
                  status=200)
    url = film2trello.get_film_url('https://kviff.tv/katalog/smolny-pich-aneb-pitomy-porno')

    assert url == 'https://www.csfd.cz/film/988751/'
    assert len(responses.calls) == 1
