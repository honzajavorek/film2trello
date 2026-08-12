import logging
import random
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import TypedDict

import httpx
import stamina
from lxml import html


logger = logging.getLogger("film2trello.http")


class RetryTransport(httpx.AsyncBaseTransport):
    """Retries safe requests that fail with transport-level errors such as
    timeouts (incl. ReadTimeout) or connection resets."""

    # Only safe (idempotent) methods are replayed. A timed-out POST/PUT may
    # have already reached the server, so retrying it could duplicate a write.
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport,
        attempts: int = 3,
    ) -> None:
        self.transport = transport
        self.attempts = attempts

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method not in self.SAFE_METHODS:
            return await self.transport.handle_async_request(request)
        send = stamina.retry(on=httpx.TransportError, attempts=self.attempts)(
            self.transport.handle_async_request
        )
        return await send(request)

    async def aclose(self) -> None:
        await self.transport.aclose()


def get_transport() -> httpx.AsyncBaseTransport:
    return RetryTransport(httpx.AsyncHTTPTransport(http2=True))


BROWSER_PROFILES: tuple[dict[str, str], ...] = (
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Sec-Ch-Ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Sec-Ch-Ua": '"Microsoft Edge";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:149.0) Gecko/20100101 Firefox/149.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9,cs;q=0.8,sk;q=0.7,es;q=0.6",
        "DNT": "1",
        "Sec-Gpc": "1",
        "TE": "trailers",
    },
)


BASE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


ANTIBOT_RETRY_ATTEMPTS = 5

ANUBIS_CHALLENGE_SELECTOR = "script#anubis_challenge"


def get_default_headers() -> dict[str, str]:
    profile = random.choice(BROWSER_PROFILES)
    return {**BASE_HEADERS, **profile}


def get_scraper() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers=get_default_headers(),
        follow_redirects=True,
        transport=get_transport(),
        event_hooks={"response": [raise_on_error]},
    )


async def raise_on_error(response: httpx.Response) -> None:
    if response.is_client_error or response.is_server_error:
        await response.aread()
        response.raise_for_status()


def with_scraper(fn: Callable[..., Coroutine]) -> Callable[..., Coroutine]:
    @wraps(fn)
    async def wrapper(*args, **kwargs) -> Coroutine:
        async with get_scraper() as client:
            return await fn(client, *args, **kwargs)

    return wrapper


class Page(TypedDict):
    request_url: str
    url: str
    html: html.HtmlElement


class AntiBotError(RuntimeError):
    pass


def is_antibot_page(page_html: html.HtmlElement) -> bool:
    return bool(page_html.cssselect(ANUBIS_CHALLENGE_SELECTOR))


async def get_html(scraper: httpx.AsyncClient, url: str) -> Page:
    @stamina.retry(
        on=AntiBotError,
        attempts=ANTIBOT_RETRY_ATTEMPTS,
    )
    async def fetch_page() -> Page:
        response = await scraper.get(url, headers=get_default_headers())
        page_url = str(response.url)
        page_html = html.fromstring(response.content)
        if is_antibot_page(page_html):
            logger.warning("Anubis challenge (request_url=%s, url=%s)", url, page_url)
            raise AntiBotError(f"Anubis challenge (request_url={url}, url={page_url})")
        page_html.make_links_absolute(page_url)
        return Page(request_url=url, url=page_url, html=page_html)

    return await fetch_page()
