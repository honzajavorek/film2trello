import asyncio
from io import BytesIO
import logging
from pprint import pformat
import re
from typing import Any, Iterable, Literal, cast

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
) -> dict[str, Any]:
    async with get_scraper() as scraper:
        if match := KVIFF_URL_RE.search(message_text):
            input_url = match.group(0)
            logger.info(f"Detected KVIFF.TV URL, scraping: {input_url}")
            response = await scraper.get(input_url)
            csfd_url = find_csfd_url(response.iter_lines())
        elif match := CSFD_URL_RE.search(message_text):
            logger.info("Detected CSFD.cz URL")
            input_url = csfd_url = match.group(0)
        else:
            raise ValueError("Could not find a valid film URL")

        logger.info(f"Scraping CSFD.cz URL: {csfd_url}")
        response = await scraper.get(csfd_url)
        csfd_url = str(response.url)
        csfd_html_tree = html.fromstring(response.content)

        target_url = csfd.parse_target_url(csfd_html_tree)
        if target_url == csfd_url:
            target_html_tree = csfd_html_tree
        else:
            logger.info(f"Detected different target URL, scraping: {target_url}")
            response = await scraper.get(target_url)
            target_html_tree = html.fromstring(response.content)

        parent_url = csfd.get_parent_url(csfd_url)
        if parent_url == csfd_url:
            parent_html_tree = csfd_html_tree
        elif parent_url == target_url:
            parent_html_tree = target_html_tree
        else:
            logger.info(f"Detected different parent URL, scraping: {parent_url}")
            response = await scraper.get(parent_url)
            parent_html_tree = html.fromstring(response.content)

    data = dict(
        input_url=input_url,
        csfd_url=target_url,
        title=csfd.parse_title(target_html_tree),
        poster_url=csfd.parse_poster_url(target_html_tree),
        durations=list(csfd.parse_durations(target_html_tree)),
        kvifftv_url=csfd.parse_kvifftv_url(parent_html_tree),
    )
    logger.debug(f"Scraped data:\n{pformat(data)}")

    async with get_trello_api(trello_key, trello_token) as trello_api:
        logger.info(f"Checking if user '{username}' is allowed to the board")
        members = (await trello_api.get(f"/boards/{board_id}/members")).json()
        if trello.not_in_members(username, members):
            raise ValueError(f"User '{username}' is not allowed to the board")

        logger.info("Analyzing columns, assuming first is inbox and last is archive")
        lists = (await trello_api.get(f"/boards/{board_id}/lists")).json()
        inbox_list_id = trello.get_inbox_id(lists)
        archive_list_id = trello.get_archive_id(lists)

        logger.info("Getting cards from both inbox and archive")
        inbox_cards = (await trello_api.get(f"/lists/{inbox_list_id}/cards")).json()
        archive_cards = (await trello_api.get(f"/lists/{archive_list_id}/cards")).json()
        cards = inbox_cards + archive_cards

        logger.info("Checking if card already exists")
        if card_id := trello.find_card_id(
            cards,
            cast(str, data["title"]),
            cast(str, data["csfd_url"]),
        ):
            logger.info(f"Card already exists, updating: {card_id}")
            await trello_api.put(
                f"/cards/{card_id}/",
                json=dict(
                    idList=inbox_list_id,
                    pos="top",
                ),
            )
        else:
            logger.info("Card does not exist, creating")
            card_id = (
                await trello_api.post(
                    "/cards",
                    json=dict(
                        name=data["title"],
                        desc=data["csfd_url"],
                        pos="top",
                        idList=inbox_list_id,
                    ),
                )
            ).json()["id"]
            logger.info(f"Card created: {card_id}")

        logger.info("Updating members")
        card_members = (await trello_api.get(f"/cards/{card_id}/members")).json()
        if trello.not_in_members(username, card_members):
            user_id = (await trello_api.get(f"/members/{username}")).json()["id"]
            await trello_api.post(
                f"/cards/{card_id}/members",
                json=dict(value=user_id),
            )

        logger.info("Updating labels")
        card_labels = (await trello_api.get(f"/cards/{card_id}/labels")).json()
        labels = trello.prepare_duration_labels(cast(list[int], data["durations"]))
        if data.get("kvifftv_url"):
            labels.append(trello.KVIFFTV_LABEL)
        labels = trello.get_missing_labels(card_labels, labels)
        for label in labels:
            try:
                await trello_api.post(f"/cards/{card_id}/labels", params=label)
            except httpx.HTTPStatusError as e:
                if "label is already on the card" not in e.response.text:
                    raise e

        logger.info("Updating attachments")
        card_attachments = (
            await trello_api.get(f"/cards/{card_id}/attachments")
        ).json()
        urls = [cast(str, data["csfd_url"])]
        if data.get("kvifftv_url"):
            urls.append(cast(str, data["kvifftv_url"]))
        urls = trello.get_missing_attached_urls(card_attachments, urls)
        await asyncio.gather(
            *(
                trello_api.post(f"/cards/{card_id}/attachments", json=dict(url=url))
                for url in urls
            )
        )
        if not trello.has_poster(card_attachments) and data["poster_url"]:
            async with get_scraper().stream(
                "GET", cast(str, data["poster_url"])
            ) as response:
                file = await create_thumbnail(response)
                await trello_api.post(
                    f"/cards/{card_id}/attachments",
                    files=dict(file=file),
                )

    card_url = f"https://trello.com/c/{card_id}"
    logger.info(f"Done processing: {card_url}")
    data["card_url"] = card_url
    return data


def get_scraper() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        http2=True,
        event_hooks={"response": [raise_on_4xx_5xx]},
    )


def get_trello_api(key: str, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://trello.com/1/",
        params=dict(key=key, token=token),
        headers={
            "User-Agent": "film2trello (+https://github.com/honzajavorek/film2trello)"
        },
        http2=True,
        event_hooks={"response": [raise_on_4xx_5xx]},
    )


def find_csfd_url(response_lines: Iterable[str]) -> str:
    for line in response_lines:
        match = CSFD_URL_RE.search(line)
        if match:
            return match.group(0)
    raise ValueError("Could not find URL pointing to CSFD.cz")


async def raise_on_4xx_5xx(response: httpx.Response) -> None:
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
