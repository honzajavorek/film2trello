from lxml import html
from pathlib import Path

import pytest

from film2trello import csfd


@pytest.fixture()
def csfd_html():
    path = Path(__file__).parent / 'csfd.html'
    return html.fromstring(path.read_text())


@pytest.mark.parametrize('url', (
    'http://csfd.cz/film/8283-posledni-skaut/',
    'http://www.csfd.cz/film/8283-posledni-skaut/',
    'https://www.csfd.cz/film/8283-posledni-skaut/',
    'https://www.csfd.cz/film/8283-posledni-skaut/prehled/',
    'https://www.csfd.cz/film/8283-posledni-skaut/komentare/'
))
def test_normalize_url(url):
    assert csfd.normalize_url(url) == 'https://www.csfd.cz/film/8283/'


@pytest.mark.parametrize('url', (
    'hello world',
    'https://www.imdb.com/title/tt3864916/',
    'https://www.csfd.cz/dvd-a-bluray/mesicne/',
))
def test_normalize_url_error(url):
    with pytest.raises(ValueError):
        csfd.normalize_url(url)


def test_parse_title(csfd_html):
    title = 'Poslední skaut / The Last Boy Scout (1991)'
    assert csfd.parse_title(csfd_html) == title


def test_parse_title_same_name():
    path = Path(__file__).parent / 'csfd_same_name.html'
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == '1917 (2019)'


def test_parse_title_no_other_name():
    path = Path(__file__).parent / 'csfd_no_other_name.html'
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == 'The Beginning of Life (2016)'


def test_parse_poster_url(csfd_html):
    url = ('https://image.pmgstatic.com/cache/resized/w420/'
           'files/images/film/posters/159/527/159527985_335bf7.jpg')
    assert csfd.parse_poster_url(csfd_html) == url


def test_parse_poster_url_no_image():
    path = Path(__file__).parent / 'csfd_no_image.html'
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_poster_url(csfd_html) == None


def test_parse_duration(csfd_html):
    assert list(csfd.parse_durations(csfd_html)) == [105]


def test_parse_duration_multiple():
    path = Path(__file__).parent / 'csfd_directors_cut.html'
    csfd_html = html.fromstring(path.read_text())

    assert list(csfd.parse_durations(csfd_html)) == [172, 208, 228]


def test_parse_duration_tvshow():
    path = Path(__file__).parent / 'csfd_tvshow.html'
    csfd_html = html.fromstring(path.read_text())

    assert list(csfd.parse_durations(csfd_html)) == [59, 65]


def test_parse_kvifftv_url():
    path = Path(__file__).parent / 'csfd_kvifftv.html'
    csfd_html = html.fromstring(path.read_text())

    kvifftv_url = 'https://kviff.tv/katalog/smolny-pich-aneb-pitomy-porno'
    assert csfd.parse_kvifftv_url(csfd_html) == kvifftv_url


def test_parse_kvifftv_url_missing(csfd_html):
    assert csfd.parse_kvifftv_url(csfd_html) is None
