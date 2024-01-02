import logging
import re
from typing import Any

from lxml import html
import httpx

from film2trello import csfd


KVIFF_URL_RE = re.compile(r"https?://(www\.)?kviff\.tv/katalog/\S+")

CSFD_URL_RE = re.compile(r"https?://(www\.)?csfd\.cz/film/[^\s\"']+")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) "
    "Gecko/20100101 Firefox/72.0"
)


logger = logging.getLogger("film2trello.core")


async def process_message(message_text: str) -> dict[str, Any]:
    if match := KVIFF_URL_RE.search(message_text):
        input_url = match.group(0)
        logger.info(f"Detected KVIFF.TV URL, scraping: {input_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                input_url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
            response.raise_for_status()
            csfd_url = None
            for line in response.iter_lines():
                match = CSFD_URL_RE.search(line)
                if match:
                    csfd_url = match.group(0)
                    break
            if not csfd_url:
                raise ValueError("KVIFF.TV page doesn't contain CSFD.cz URL")
    elif match := CSFD_URL_RE.search(message_text):
        logger.info("Detected CSFD.cz URL")
        input_url = csfd_url = match.group(0)
    else:
        raise ValueError("Could not find a valid film URL")

    logger.info(f"Scraping CSFD.cz URL: {csfd_url}")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            csfd_url,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
        response.raise_for_status()
        csfd_url = str(response.url)
        csfd_html_tree = html.fromstring(response.content)

    target_url = csfd.parse_target_url(csfd_html_tree)
    if target_url == csfd_url:
        target_html_tree = csfd_html_tree
    else:
        logger.info(f"Detected different target URL, scraping: {target_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                target_url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
            response.raise_for_status()
            target_html_tree = html.fromstring(response.content)

    parent_url = csfd.get_parent_url(csfd_url)
    if parent_url == csfd_url:
        parent_html_tree = csfd_html_tree
    elif parent_url == target_url:
        parent_html_tree = target_html_tree
    else:
        logger.info(f"Detected different parent URL, scraping: {parent_url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                parent_url,
                headers={"User-Agent": USER_AGENT},
                follow_redirects=True,
            )
            response.raise_for_status()
            parent_html_tree = html.fromstring(response.content)

    return dict(
        input_url=input_url,
        csfd_url=target_url,
        title=csfd.parse_title(target_html_tree),
        poster_url=csfd.parse_poster_url(target_html_tree),
        durations=list(csfd.parse_durations(target_html_tree)),
        kvifftv_url=csfd.parse_kvifftv_url(parent_html_tree),
    )
