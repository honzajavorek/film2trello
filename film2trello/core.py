import logging
import re
from typing import Any, Iterable

import httpx
from lxml import html

from film2trello import csfd


KVIFF_URL_RE = re.compile(r"https?://(www\.)?kviff\.tv/katalog/\S+")

CSFD_URL_RE = re.compile(r"https?://(www\.)?csfd\.cz/film/[^\s\"']+")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) "
    "Gecko/20100101 Firefox/72.0"
)


logger = logging.getLogger("film2trello.core")


async def process_message(
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

    async with get_trello_api(trello_key, trello_token) as trello_api:
        response = await trello_api.get(f"/boards/{board_id}/members")
        print(response.json())  # TODO

    return dict(
        input_url=input_url,
        csfd_url=target_url,
        title=csfd.parse_title(target_html_tree),
        poster_url=csfd.parse_poster_url(target_html_tree),
        durations=list(csfd.parse_durations(target_html_tree)),
        kvifftv_url=csfd.parse_kvifftv_url(parent_html_tree),
    )


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


async def raise_on_4xx_5xx(response: httpx.Response):
    response.raise_for_status()
