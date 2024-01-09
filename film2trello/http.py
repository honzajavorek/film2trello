from functools import wraps
from typing import Any, AsyncGenerator, Callable, Coroutine, TypeVar, TypedDict, cast
import httpx
from lxml import html


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) "
    "Gecko/20100101 Firefox/72.0"
)


def get_scraper() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        http2=True,
        event_hooks={"response": [raise_on_error]},
    )


async def raise_on_error(response: httpx.Response) -> None:
    if response.is_client_error or response.is_server_error:
        response.raise_for_status()


def with_scraper(fn: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
    @wraps(fn)
    async def wrapper(*args, **kwargs) -> Coroutine:
        async with get_scraper() as client:
            return await fn(client, *args, **kwargs)

    return wrapper


class Page(TypedDict):
    url: str
    html: html.HtmlElement


async def get_html(scraper: httpx.AsyncClient, url: str) -> Page:
    response = await scraper.get(url)
    page_url = str(response.url)
    page_html = html.fromstring(response.content)
    page_html.make_links_absolute(page_url)
    return Page(url=page_url, html=page_html)
