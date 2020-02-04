from lxml import html
from pathlib import Path

import pytest

from film2trello import csfd


@pytest.fixture()
def csfd_html():
    path = Path(__file__).parent / 'csfd.html'
    return html.fromstring(path.read_text())


@pytest.fixture()
def csfd_directors_cut_html():
    path = Path(__file__).parent / 'csfd_directors_cut.html'
    return html.fromstring(path.read_text())


@pytest.fixture()
def csfd_tvshow_html():
    path = Path(__file__).parent / 'csfd_tvshow.html'
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


def test_parse_poster_url(csfd_html):
    url = ('https://img.csfd.cz/files/images/film/posters/159/527/'
           '159527985_335bf7.jpg')
    assert csfd.parse_poster_url(csfd_html) == url


def test_parse_duration(csfd_html):
    assert list(csfd.parse_durations(csfd_html)) == [105]


def test_parse_duration_multiple(csfd_directors_cut_html):
    assert list(csfd.parse_durations(csfd_directors_cut_html)) == [172, 208, 228]


def test_parse_duration_tvshow(csfd_tvshow_html):
    assert list(csfd.parse_durations(csfd_tvshow_html)) == [59, 65]
