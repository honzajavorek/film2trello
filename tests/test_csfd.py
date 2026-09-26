import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock

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


def test_get_base_url_from_canonical():
    csfd_html = html.fromstring(
        '<link rel="canonical" href="https://www.csfd.cz/film/1-foo/">'
    )

    assert csfd.get_base_url(csfd_html) == "https://www.csfd.cz/film/1-foo/"


def test_get_base_url_falls_back_to_og_url():
    csfd_html = html.fromstring(
        '<meta property="og:url" content="https://www.csfd.cz/film/1-foo/">'
    )

    assert csfd.get_base_url(csfd_html) == "https://www.csfd.cz/film/1-foo/"


def test_get_base_url_skips_canonical_without_href():
    csfd_html = html.fromstring(
        "<html><head>"
        '<link rel="canonical">'
        '<meta property="og:url" content="https://www.csfd.cz/film/1-foo/">'
        "</head></html>"
    )

    assert csfd.get_base_url(csfd_html) == "https://www.csfd.cz/film/1-foo/"


def test_get_base_url_raises_when_missing():
    csfd_html = html.fromstring("<html><head></head></html>")

    with pytest.raises(ValueError):
        csfd.get_base_url(csfd_html)


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

    assert list(csfd.parse_durations(csfd_html)) == [172, 208, 228, 219]


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


def test_parse_csfd_url():
    path = Path(__file__).parent / "kvifftv.html"
    kvifftv_html = html.fromstring(path.read_text())

    assert csfd.parse_csfd_url(kvifftv_html) == "https://www.csfd.cz/film/988751"


def test_parse_csfd_url_missing():
    kvifftv_html = html.fromstring("<html><body>no link here</body></html>")

    assert csfd.parse_csfd_url(kvifftv_html) is None


@pytest.mark.parametrize(
    "filename, expected",
    (
        (
            "csfd.html",
            "https://www.csfd.cz/film/8283-posledni-skaut/prehled/",
        ),
        (
            "csfd_tvshow.html",
            "https://www.csfd.cz/film/1184280-medved/1184281-serie-1/prehled/",
        ),
        (
            "csfd_tvshow_e.html",
            "https://www.csfd.cz/film/683975-cernobyl/prehled/",
        ),
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
    ),
)
def test_get_parent_url(csfd_url, expected):
    assert csfd.get_parent_url(csfd_url) == expected


@pytest.mark.parametrize(
    "filename, expected",
    (
        ("csfd.html", False),
        ("csfd_tvshow_e.html", True),
        ("csfd_tvshow_s.html", True),
        ("csfd_tvshow_s_e.html", True),
        ("csfd_missing_overview.html", False),
    ),
)
def test_parse_is_tvshow_true(filename, expected):
    path = Path(__file__).parent / filename
    csfd_html = html.fromstring(path.read_text())

    assert csfd.parse_is_tvshow(csfd_html) is expected


@pytest.mark.parametrize(
    "fixture_name",
    ["csfd_antibot_cs.html", "csfd_antibot_en.html"],
)
def test_is_antibot_page_detects_anubis_challenge(fixture_name):
    path = Path(__file__).parent / fixture_name
    page_html = html.fromstring(path.read_text())

    assert csfd.is_antibot_page(page_html) is True


def test_is_antibot_page_ignores_regular_page(csfd_html):
    assert csfd.is_antibot_page(csfd_html) is False


class FakePage:
    def __init__(self, url: str) -> None:
        self.url = url
        self.closed = False

    async def goto(self, url: str, **kwargs) -> None:
        pass

    def locator(self, selector: str):
        return AsyncMock(count=AsyncMock(return_value=0))

    async def title(self) -> str:
        return "Film"

    async def content(self) -> str:
        return "<html><body>Film</body></html>"

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_browser_session_get_html_logs_progress_and_closes_page(caplog):
    page = FakePage("https://www.csfd.cz/film/1-film/prehled/")
    session = csfd.BrowserSession()
    session._browser = AsyncMock(new_page=AsyncMock(return_value=page))

    with caplog.at_level(logging.INFO, logger="film2trello.csfd"):
        await session.get_html("https://www.csfd.cz/film/1-film/")

    assert page.closed
    assert "Loading https://www.csfd.cz/film/1-film/ (attempt 1/3)" in caplog.text
    assert "Loaded https://www.csfd.cz/film/1-film/prehled/ in" in caplog.text


@pytest.mark.asyncio
async def test_browser_session_open_times_out_when_launch_hangs(monkeypatch):
    class HangingCamoufox:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self):
            await asyncio.sleep(3600)

    monkeypatch.setattr(csfd, "AsyncCamoufox", HangingCamoufox)
    monkeypatch.setattr(csfd, "LAUNCH_TIMEOUT", 0.01)

    with pytest.raises(TimeoutError):
        await csfd.BrowserSession().open()
