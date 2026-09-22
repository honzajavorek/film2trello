import logging
import random
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any

import httpx
import stamina


logger = logging.getLogger("film2trello.http")


class RateLimitedError(Exception):
    def __init__(self, response: httpx.Response) -> None:
        self.response = response


class RetryTransport(httpx.AsyncBaseTransport):
    """Retries safe requests that fail with transport-level errors such as
    timeouts (incl. ReadTimeout) or connection resets, and retries a 429
    response for any method. A 429 means the server rejected the request
    before ever processing it, so unlike a timed-out POST/PUT (which may
    have already reached the server), retrying it can't duplicate a write.
    """

    # Only safe (idempotent) methods are replayed on a transport error. A
    # timed-out POST/PUT may have already reached the server, so retrying
    # it could duplicate a write.
    SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

    def __init__(
        self,
        transport: httpx.AsyncBaseTransport,
        attempts: int = 3,
    ) -> None:
        self.transport = transport
        self.attempts = attempts

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        async def send() -> httpx.Response:
            if request.method not in self.SAFE_METHODS:
                response = await self.transport.handle_async_request(request)
            else:
                retry_transport_errors = stamina.retry(
                    on=httpx.TransportError, attempts=self.attempts
                )(self.transport.handle_async_request)
                response = await retry_transport_errors(request)

            if response.status_code == 429:
                await response.aread()
                raise RateLimitedError(response)
            return response

        try:
            retry_rate_limits = stamina.retry(on=RateLimitedError)(send)
            return await retry_rate_limits()
        except RateLimitedError as exc:
            # Retries exhausted; hand back the still-429 response so callers
            # see the same httpx.HTTPStatusError they'd get without any of
            # this retrying (e.g. via the raise_on_error event hook).
            return exc.response

    async def aclose(self) -> None:
        await self.transport.aclose()


def get_transport() -> httpx.AsyncBaseTransport:
    return RetryTransport(httpx.AsyncHTTPTransport(http2=True))


BROWSER_PROFILES: tuple[dict[str, str], ...] = (
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Sec-Ch-Ua": '"Google Chrome";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Sec-Ch-Ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Sec-Ch-Ua": '"Microsoft Edge";v="130", "Chromium";v="130", "Not_A Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
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
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def get_default_headers() -> dict[str, str]:
    profile = random.choice(BROWSER_PROFILES)
    return {**BASE_HEADERS, **profile}


def get_scraper() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=True,
        transport=get_transport(),
        event_hooks={"response": [raise_on_error]},
    )


async def raise_on_error(response: httpx.Response) -> None:
    if response.is_client_error or response.is_server_error:
        await response.aread()
        response.raise_for_status()


def with_scraper[R](
    fn: Callable[..., Coroutine[Any, Any, R]],
) -> Callable[..., Coroutine[Any, Any, R]]:
    @wraps(fn)
    async def wrapper(*args, **kwargs) -> R:
        async with get_scraper() as client:
            return await fn(client, *args, **kwargs)

    return wrapper
