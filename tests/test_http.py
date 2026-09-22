import httpx
import pytest
import stamina

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


@pytest.mark.asyncio
async def test_retry_transport_retries_rate_limited_get():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, text="ok")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.com/")

    assert response.status_code == 200
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_retry_transport_retries_rate_limited_put():
    # Every PUT this codebase sends is idempotent (absolute values, never
    # increments), so it's safe to retry even though POST isn't.
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, text="rate limited")
        return httpx.Response(200, text="ok")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.put("https://example.com/", json={"foo": "bar"})

    assert response.status_code == 200
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_retry_transport_does_not_retry_rate_limited_post():
    # POST isn't idempotent (e.g. creating a card), and Trello doesn't
    # document whether a 429 can follow a write it already committed, so
    # this is left to propagate rather than risk a duplicate.
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, text="rate limited")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.post("https://example.com/", json={"foo": "bar"})

    assert response.status_code == 429
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_retry_transport_gives_up_and_returns_last_rate_limited_response():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, text="rate limited")

    transport = http.RetryTransport(httpx.MockTransport(handler))
    async with httpx.AsyncClient(transport=transport) as client:
        response = await client.get("https://example.com/")

    assert response.status_code == 429
    assert len(calls) > 1
