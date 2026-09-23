from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from diskcache import Cache

from film2trello import core


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "cache", Cache(str(tmp_path / "cache")))


@pytest.mark.asyncio
async def test_get_film_by_url_skips_scraping_on_second_call(monkeypatch):
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

    async def fake_get_csfd_pages(csfd_url, session):
        calls.append(csfd_url)
        return {}

    monkeypatch.setattr(core, "get_csfd_pages", fake_get_csfd_pages)
    monkeypatch.setattr(core, "get_film", lambda pages: film)

    url = film["csfd_url"]
    session = object()
    first = await core.get_film_by_url(url, session)
    second = await core.get_film_by_url(url, session)

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


@pytest.fixture
def film() -> core.Film:
    return core.Film(
        title="Foo (2020)",
        csfd_url="https://www.csfd.cz/film/1-foo/prehled/",
        poster_url="https://example.com/poster.jpg",
        kvifftv_url="https://kviff.tv/katalog/foo",
        netflix_url="https://netflix.com/title/1",
        durations=[100],
        is_tvshow=False,
    )


@pytest.fixture
def film_session(monkeypatch: pytest.MonkeyPatch, film: core.Film) -> None:
    @asynccontextmanager
    async def browser_session() -> AsyncIterator[object]:
        yield object()

    monkeypatch.setattr(core.csfd, "browser_session", browser_session)
    monkeypatch.setattr(core, "get_film_by_url", AsyncMock(return_value=film))


@pytest.mark.asyncio
@pytest.mark.parametrize("existing", [True, False])
async def test_process_message_preserves_card_steps(
    monkeypatch: pytest.MonkeyPatch, film_session: None, film: core.Film, existing: bool
) -> None:
    card = {"id": "old", "name": film["title"], "desc": film["csfd_url"]}
    update = AsyncMock()
    create = AsyncMock(return_value="new")
    join = AsyncMock()
    labels = AsyncMock()
    attachments = AsyncMock(return_value=["poster failed"])
    for name, handler in {
        "check_username": AsyncMock(),
        "get_working_lists_ids": AsyncMock(return_value=["inbox", "archive"]),
        "get_cards": AsyncMock(return_value=[card] if existing else []),
        "update_card": update,
        "create_card": create,
        "join_card": join,
        "update_card_labels": labels,
        "update_card_attachments": attachments,
    }.items():
        monkeypatch.setattr(core.trello, name, handler)

    messages = [
        message
        async for message in core.process_message(
            object(), object(), "alice", film["csfd_url"], "board"
        )
    ]

    card_id = "old" if existing else "new"
    assert (update.await_count, create.await_count) == ((1, 0) if existing else (0, 1))
    assert join.await_args.args[1:] == (card_id, "alice")
    assert labels.await_args.args[1:] == (card_id, core.get_labels(film))
    assert attachments.await_args.args[2:] == (
        card_id,
        [film["csfd_url"], film["kvifftv_url"]],
        film["poster_url"],
    )
    assert messages[-2:] == [
        "poster failed",
        f"Done! This is your card: https://trello.com/c/{card_id}",
    ]
    assert ("Card already exists, updating" in messages[5]) is existing


@pytest.mark.asyncio
async def test_process_inbox_skips_unlinked_cards_and_preserves_updates(
    monkeypatch: pytest.MonkeyPatch, film_session: None, film: core.Film
) -> None:
    card = {"id": "1", "name": "Old title", "desc": film["csfd_url"], "labels": []}
    skipped = {"id": "2", "name": "Unlinked", "desc": "", "labels": []}
    archive = AsyncMock()
    update = AsyncMock()
    labels = AsyncMock()
    attachments = AsyncMock(return_value=[])
    position = AsyncMock()
    for name, handler in {
        "get_working_lists_ids": AsyncMock(return_value=["inbox", "archive"]),
        "get_old_cards": AsyncMock(return_value=[skipped]),
        "archive_cards": archive,
        "get_cards": AsyncMock(return_value=[card, skipped]),
        "update_card": update,
        "update_card_labels": labels,
        "update_card_attachments": attachments,
        "update_card_position": position,
    }.items():
        monkeypatch.setattr(core.trello, name, handler)

    # Bypass only the client-creation decorators; keep the real inbox workflow.
    await core.process_inbox.__wrapped__.__wrapped__(object(), object(), "board")

    assert archive.await_args.args[1:] == ("archive", [skipped])
    assert update.await_args.args[1:] == (
        "1",
        {"name": film["title"], "desc": film["csfd_url"]},
    )
    assert labels.await_args.args[1:] == ("1", core.get_labels(film))
    assert attachments.await_args.args[2:] == (
        "1",
        [film["csfd_url"], film["kvifftv_url"], film["netflix_url"]],
        film["poster_url"],
    )
    assert position.await_args.args[1:] == ("1", 1)


@pytest.mark.asyncio
async def test_get_csfd_pages_reuses_redirect_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = "https://www.csfd.cz/film/1/prehled/"
    target = "https://www.csfd.cz/film/1/season/prehled/"
    parent = "https://www.csfd.cz/film/1/"
    first = {"request_url": base, "url": base, "html": object()}
    redirected = {"request_url": target, "url": parent, "html": object()}
    session = SimpleNamespace(get_html=AsyncMock(side_effect=[first, redirected]))
    monkeypatch.setattr(core.csfd, "parse_target_url", lambda html: target)
    monkeypatch.setattr(core.csfd, "get_parent_url", lambda url: parent)

    pages = await core.get_csfd_pages(base, session)

    assert pages == {"target": redirected, "parent": redirected}
    assert session.get_html.await_count == 2
