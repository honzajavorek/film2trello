import asyncio
from datetime import date, timedelta
from io import BytesIO
import logging
import re
from typing import AsyncGenerator, Iterable, Literal

import httpx
from lxml import html
from PIL import Image

from film2trello import csfd, trello


KVIFF_URL_RE = re.compile(r"https?://(www\.)?kviff\.tv/katalog/\S+")

CSFD_URL_RE = re.compile(r"https?://(www\.)?csfd\.cz/film/[^\s\"']+")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) "
    "Gecko/20100101 Firefox/72.0"
)

THUMBNAIL_SIZE = (500, 500)


logger = logging.getLogger("film2trello.core")


async def process_message(
    username: str,
    message_text: str,
    board_id: str,
    trello_key: str,
    trello_token: str,
) -> AsyncGenerator[str, None]:
    if match := KVIFF_URL_RE.search(message_text):
        input_url = match.group(0)
        yield f"Detected KVIFF.TV URL, scraping: {input_url}"
        async with get_scraper() as scraper:
            response = await scraper.get(input_url)
        csfd_url = find_csfd_url(response.iter_lines())
    elif match := CSFD_URL_RE.search(message_text):
        yield "Detected CSFD.cz URL"
        csfd_url = match.group(0)
    else:
        raise ValueError("Could not find a valid film URL")
    async for message in process_url(
        csfd_url,
        board_id,
        trello_key,
        trello_token,
        username=username,
    ):
        yield message


async def process_inbox(board_id: str, trello_key: str, trello_token: str) -> None:
    async with get_trello_api(trello_key, trello_token) as trello_api:
        lists = (await trello_api.get(f"/boards/{board_id}/lists")).json()
        inbox_list_id = trello.get_inbox_id(lists)
        archive_list_id = trello.get_archive_id(lists)

        years_ago = date.today() - timedelta(days=365 * 2)
        years_old_cards = (
            await trello_api.get(f"/lists/{inbox_list_id}/cards?before={years_ago}")
        ).json()
        logger.info(f"Found {len(years_old_cards)} years old cards")

        for card in years_old_cards:
            logger.info(
                f"Archiving card: {card['name']} {trello.get_card_url(card['id'])}"
            )
            await trello_api.put(
                f"/cards/{card['id']}/",
                json=dict(idList=archive_list_id),
            )

        cards = (await trello_api.get(f"/lists/{inbox_list_id}/cards")).json()
        column = [{"card": card} for card in cards]

        for item in column:
            card = item["card"]
            logger.info(
                f"Processing card: {card['name']} {trello.get_card_url(card['id'])}"
            )
            if match := CSFD_URL_RE.search(card["desc"]):
                csfd_url = match.group(0)
                logger.info(f"CSFD.cz URL: {csfd_url}")
                async for message in process_url(
                    csfd_url,
                    board_id,
                    trello_key,
                    trello_token,
                    card_id=card["id"],
                ):
                    logger.info(f"Status: {message}")
            else:
                logger.info("Card description doesn't contain CSFD.cz URL")

    # def sort_key(item):
    #     film, card = item["film"], item["card"]

    #     min_duration = min(film["durations"]) if (film and film["durations"]) else 1000
    #     labels = [label["name"].lower() for label in card["labels"] or []]
    #     is_available = 0 if (("kviff.tv" in labels) or ("stash" in labels)) else 1

    #     return (min_duration, is_available, card["name"])

    # for pos, item in enumerate(sorted(column, key=sort_key), start=1):
    #     print(f"#{pos}", item["card"]["name"], file=sys.stderr, flush=True)
    #     api.put(f"/cards/{item['card']['id']}/", data=dict(pos=pos))
    #     time.sleep(0.5)
    pass


async def process_url(
    csfd_url: str,
    board_id: str,
    trello_key: str,
    trello_token: str,
    card_id: str | None = None,
    username: str | None = None,
) -> AsyncGenerator[str, None]:
    async with get_scraper() as scraper:
        yield f"Scraping CSFD.cz URL: {csfd_url}"
        response = await scraper.get(csfd_url)
        csfd_url = str(response.url)
        csfd_html_tree = html.fromstring(response.content)

        target_url = csfd.parse_target_url(csfd_html_tree)
        if target_url == csfd_url:
            target_html_tree = csfd_html_tree
        else:
            yield f"Detected different target URL, scraping: {target_url}"
            response = await scraper.get(target_url)
            target_html_tree = html.fromstring(response.content)

        parent_url = csfd.get_parent_url(csfd_url)
        if parent_url == csfd_url:
            parent_html_tree = csfd_html_tree
        elif parent_url == target_url:
            parent_html_tree = target_html_tree
        else:
            yield f"Detected different parent URL, scraping: {parent_url}"
            response = await scraper.get(parent_url)
            parent_html_tree = html.fromstring(response.content)

    title = csfd.parse_title(target_html_tree)
    logger.debug(f"Title: {title}")
    poster_url = csfd.parse_poster_url(target_html_tree)
    logger.debug(f"Poster URL: {poster_url}")
    durations = list(csfd.parse_durations(target_html_tree))
    logger.debug(f"Durations: {durations}")
    kvifftv_url = csfd.parse_kvifftv_url(parent_html_tree)
    logger.debug(f"KVIFF.TV URL: {kvifftv_url}")

    async with get_trello_api(trello_key, trello_token) as trello_api:
        if username is not None:
            yield f"Checking if user '{username}' is allowed to the board"
            members = (await trello_api.get(f"/boards/{board_id}/members")).json()
            if trello.not_in_members(username, members):
                raise ValueError(f"User '{username}' is not allowed to the board")

        if card_id:
            card_data = dict(
                name=title,
                desc=csfd_url,
            )
        else:
            yield "Analyzing columns, assuming first is inbox and last is archive"
            lists = (await trello_api.get(f"/boards/{board_id}/lists")).json()
            inbox_list_id = trello.get_inbox_id(lists)
            archive_list_id = trello.get_archive_id(lists)

            yield "Checking if card already exists"
            inbox_cards = (await trello_api.get(f"/lists/{inbox_list_id}/cards")).json()
            archive_cards = (
                await trello_api.get(f"/lists/{archive_list_id}/cards")
            ).json()
            cards = inbox_cards + archive_cards
            card_id = trello.find_card_id(cards, title, csfd_url)
            card_data = dict(
                name=title,
                desc=csfd_url,
                pos="top",
                idList=inbox_list_id,
            )

        if card_id:
            yield f"Card already exists, updating: {trello.get_card_url(card_id)}"
            await trello_api.put(f"/cards/{card_id}/", json=card_data)
        else:
            yield "Card does not exist, creating"
            card_id = (await trello_api.post("/cards", json=card_data)).json()["id"]
            assert card_id
            yield f"Card created: {trello.get_card_url(card_id)}"

        if username is not None:
            yield "Updating members"
            card_members = (await trello_api.get(f"/cards/{card_id}/members")).json()
            if trello.not_in_members(username, card_members):
                user_id = (await trello_api.get(f"/members/{username}")).json()["id"]
                await trello_api.post(
                    f"/cards/{card_id}/members",
                    json=dict(value=user_id),
                )

        yield "Updating labels"
        card_labels = (await trello_api.get(f"/cards/{card_id}/labels")).json()
        labels = trello.prepare_duration_labels(durations)
        if kvifftv_url:
            labels.append(trello.KVIFFTV_LABEL)
        labels = trello.get_missing_labels(card_labels, labels)
        for label in labels:
            try:
                await trello_api.post(f"/cards/{card_id}/labels", params=label)
            except httpx.HTTPStatusError as e:
                if "label is already on the card" not in e.response.text:
                    raise e

        yield "Updating attachments"
        card_attachments = (
            await trello_api.get(f"/cards/{card_id}/attachments")
        ).json()
        urls = [csfd_url]
        if kvifftv_url:
            urls.append(kvifftv_url)
        urls = trello.get_missing_attached_urls(card_attachments, urls)
        await asyncio.gather(
            *(
                trello_api.post(f"/cards/{card_id}/attachments", json=dict(url=url))
                for url in urls
            )
        )
        if not trello.has_poster(card_attachments) and poster_url:
            async with get_scraper().stream("GET", poster_url) as response:
                file = await create_thumbnail(response)
                await trello_api.post(
                    f"/cards/{card_id}/attachments",
                    files=dict(file=file),
                )

    yield f"Done! This is your card: {trello.get_card_url(card_id)}"


def get_scraper() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        http2=True,
        event_hooks={"response": [raise_on_error]},
    )


def get_trello_api(key: str, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://trello.com/1/",
        params=dict(key=key, token=token),
        headers={
            "User-Agent": "film2trello (+https://github.com/honzajavorek/film2trello)"
        },
        http2=True,
        event_hooks={"response": [raise_on_error]},
    )


def find_csfd_url(response_lines: Iterable[str]) -> str:
    for line in response_lines:
        match = CSFD_URL_RE.search(line)
        if match:
            return match.group(0)
    raise ValueError("Could not find URL pointing to CSFD.cz")


async def raise_on_error(response: httpx.Response) -> None:
    if response.is_client_error or response.is_server_error:
        response.raise_for_status()


async def create_thumbnail(
    response: httpx.Response,
) -> tuple[Literal["poster.jpg"], BytesIO, Literal["image/jpeg"]]:
    in_file = BytesIO()
    async for chunk in response.aiter_bytes():
        in_file.write(chunk)
    in_file.seek(0)
    image = Image.open(in_file).convert("RGB")
    image.thumbnail(THUMBNAIL_SIZE)
    out_file = BytesIO()
    image.save(out_file, "JPEG")
    out_file.seek(0)
    return ("poster.jpg", out_file, "image/jpeg")
