from pathlib import Path

import pytest
from lxml import html

from film2trello import csfd


@pytest.fixture()
def csfd_html():
    path = Path(__file__).parent / "csfd.html"
    return html.fromstring(path.read_text())


def test_parse_title(csfd_html):
    assert csfd.parse_title(csfd_html) == "Poslední skaut / The Last Boy Scout (1991)"


def test_parse_title_same_name():
    path = Path(__file__).parent / "csfd_same_name.html"
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == "1917 (2019)"


def test_parse_title_no_other_name():
    path = Path(__file__).parent / "csfd_no_other_name.html"
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == "The Beginning of Life (2016)"


def test_parse_wip_name():
    path = Path(__file__).parent / "csfd_wip_name.html"
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == "Hranice lásky (2022)"


def test_parse_festival_name():
    path = Path(__file__).parent / "csfd_festival_name.html"
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_title(csfd_html) == "Drive My Car (2021)"


def test_parse_poster_url(csfd_html):
    assert csfd.parse_poster_url(csfd_html) == (
        "https://image.pmgstatic.com/cache/resized/w420/"
        "files/images/film/posters/159/527/159527985_335bf7.jpg"
    )


def test_parse_poster_url_no_image():
    path = Path(__file__).parent / "csfd_no_image.html"
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_poster_url(csfd_html) is None


def test_parse_duration(csfd_html):
    assert list(csfd.parse_durations(csfd_html)) == [105]


def test_parse_duration_multiple():
    path = Path(__file__).parent / "csfd_directors_cut.html"
    csfd_html = html.fromstring(path.read_text())

    assert list(csfd.parse_durations(csfd_html)) == [172, 208, 228]


@pytest.mark.parametrize(
    "filename, expected",
    (
        ("csfd_tvshow_e.html", [59, 65]),
        ("csfd_tvshow_s.html", [49, 65]),
        ("csfd_tvshow_s_e.html", [51, 65]),
    ),
)
def test_parse_duration_tvshow(filename, expected):
    path = Path(__file__).parent / filename
    csfd_html = html.fromstring(path.read_text())

    assert list(csfd.parse_durations(csfd_html)) == expected


def test_parse_kvifftv_url():
    path = Path(__file__).parent / "csfd_kvifftv.html"
    csfd_html = html.fromstring(path.read_text())

    assert (
        csfd.parse_kvifftv_url(csfd_html)
        == "https://kviff.tv/katalog/smolny-pich-aneb-pitomy-porno"
    )


def test_parse_kvifftv_url_missing(csfd_html):
    assert csfd.parse_kvifftv_url(csfd_html) is None


@pytest.mark.parametrize(
    "filename, expected",
    (
        ("csfd.html", "https://www.csfd.cz/film/8283-posledni-skaut/prehled/"),
        ("csfd_tvshow_e.html", "https://www.csfd.cz/film/683975-cernobyl/prehled/"),
        (
            "csfd_tvshow_s.html",
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/449077-serie-1/prehled/",
        ),
        (
            "csfd_tvshow_s_e.html",
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/449077-serie-1/prehled/",
        ),
        (
            "csfd_missing_overview.html",
            "https://www.csfd.cz/film/434527-the-sexual-liberation-of-anna-lee/prehled/",
        ),
    ),
)
def test_parse_target_url(filename, expected):
    path = Path(__file__).parent / filename
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_target_url(csfd_html) == expected


@pytest.mark.parametrize(
    "csfd_url, expected",
    (
        (
            "https://www.csfd.cz/film/8283-posledni-skaut/prehled/",
            "https://www.csfd.cz/film/8283-posledni-skaut/prehled/",
        ),
        (
            "https://www.csfd.cz/film/683975-cernobyl/prehled/",
            "https://www.csfd.cz/film/683975-cernobyl/prehled/",
        ),
        (
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/449077-serie-1/prehled/",
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/prehled/",
        ),
        (
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/449077-serie-1/prehled/",
            "https://www.csfd.cz/film/346500-pod-cernou-vlajkou/prehled/",
        ),
    ),
)
def test_get_parent_url(csfd_url, expected):
    assert csfd.get_parent_url(csfd_url) == expected
