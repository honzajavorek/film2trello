from pathlib import Path

import httpx
import pytest
import stamina
from lxml import html

from film2trello import http


@pytest.fixture(autouse=True)
def no_backoff():
    with stamina.set_testing(True, attempts=100, cap=True):
        yield


@pytest.mark.asyncio
async def test_retry_transport_retries_read_timeout():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 2:
            raise httpx.ReadTimeout("boom", request=request)
        return httpx.Response(200, text="ok")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.com/")

    assert response.status_code == 200
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_transport_gives_up_after_attempts():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("boom", request=request)

    transport = http.RetryTransport(httpx.MockTransport(handler), attempts=2)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.get("https://example.com/")

    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_transport_does_not_retry_unsafe_methods():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ReadTimeout("boom", request=request)

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.post("https://example.com/", json={"foo": "bar"})

    assert len(calls) == 1


@pytest.mark.parametrize(
    "fixture_name",
    ["csfd_antibot_cs.html", "csfd_antibot_en.html"],
)
def test_is_antibot_page_detects_anubis_challenge(fixture_name):
    path = Path(__file__).parent / fixture_name
    page_html = html.fromstring(path.read_text())

    assert http.is_antibot_page(page_html) is True


def test_is_antibot_page_ignores_regular_page():
    path = Path(__file__).parent / "csfd.html"
    page_html = html.fromstring(path.read_text())

    assert http.is_antibot_page(page_html) is False


@pytest.mark.asyncio
async def test_retry_transport_does_not_retry_success():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, text="ok")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.com/")

    assert response.status_code == 200
    assert len(calls) == 1
