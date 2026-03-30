from pathlib import Path

import httpx
import pytest
from lxml import html

from film2trello import core, http


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", ("csfd_antibot_cs.html", "csfd_antibot_en.html"))
async def test_get_csfd_pages_raises_runtimeerror_on_antibot(
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
):
    path = Path(__file__).parent / filename
    anti_bot_html = html.fromstring(path.read_text())

    async def fake_get_html(scraper: httpx.AsyncClient, url: str) -> http.Page:
        return http.Page(request_url=url, url=url, html=anti_bot_html)

    monkeypatch.setattr(http, "get_html", fake_get_html)

    async with httpx.AsyncClient() as scraper:
        with pytest.raises(RuntimeError, match="anti-bot protection page"):
            await core.get_csfd_pages(
                scraper=scraper,
                csfd_url="https://www.csfd.cz/film/708117-1917/prehled/",
            )
