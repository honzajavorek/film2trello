import httpx
import pytest
from diskcache import Cache

from film2trello import core


@pytest.fixture(autouse=True)
def isolated_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "film_cache", Cache(str(tmp_path / "films")))
    monkeypatch.setattr(core, "kvifftv_cache", Cache(str(tmp_path / "kvifftv")))


@pytest.mark.asyncio
async def test_get_cached_film_skips_scraping_on_second_call(monkeypatch):
    film = core.Film(
        title="Foo (2020)",
        csfd_url="https://www.csfd.cz/film/1-foo/prehled/",
        poster_url=None,
        kvifftv_url=None,
        netflix_url=None,
        durations=[100],
        is_tvshow=False,
    )
    calls = []

    async def fake_get_csfd_pages(csfd_url):
        calls.append(csfd_url)
        return {}

    monkeypatch.setattr(core, "get_csfd_pages", fake_get_csfd_pages)
    monkeypatch.setattr(core, "get_film", lambda pages: film)

    url = film["csfd_url"]
    first = await core.get_cached_film(url)
    second = await core.get_cached_film(url)

    assert first == film
    assert second == film
    assert calls == [url]


@pytest.mark.asyncio
async def test_get_csfd_url_caches_kvifftv_lookup():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            content=b'<a href="https://www.csfd.cz/film/1-foo/">CSFD</a>',
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as scraper:
        message = "https://kviff.tv/katalog/foo"
        first = await core.get_csfd_url(scraper, message)
        second = await core.get_csfd_url(scraper, message)

    assert first == "https://www.csfd.cz/film/1-foo/"
    assert second == "https://www.csfd.cz/film/1-foo/"
    assert len(calls) == 1
