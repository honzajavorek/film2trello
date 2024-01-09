from datetime import date, timedelta
import logging
from pprint import pformat
from typing import AsyncGenerator, TypedDict

import httpx

from film2trello import csfd, trello, http


logger = logging.getLogger("film2trello.core")


class Film(TypedDict):
    title: str
    csfd_url: str
    poster_url: str | None
    kvifftv_url: str | None
    durations: list[int]


async def process_message(
    scraper: httpx.AsyncClient,
    trello_api: httpx.AsyncClient,
    username: str,
    message_text: str,
    board_id: str,
) -> AsyncGenerator[str, None]:
    yield "Figuring out CSFD.cz URL…"
    csfd_url = await get_csfd_url(scraper, message_text)

    yield "Scraping information from CSFD.cz…"
    pages = await get_csfd_pages(scraper, csfd_url)
    film = get_film(csfd_url, pages)
    logger.info(f"Film:\n{pformat(film)}")

    yield f"Checking if user '{username}' is allowed to the board"
    await trello.check_username(trello_api, board_id, username)

    yield "Analyzing columns, assuming first is inbox and last is archive"
    lists_ids = await trello.get_working_lists_ids(trello_api, board_id)
    inbox_list_id = lists_ids[0]

    yield "Checking if card already exists"
    cards = await trello.get_cards(trello_api, lists_ids)
    card_id = trello.find_card_id(cards, film["title"], film["csfd_url"])
    card_data = trello.prepare_card_data(
        film["title"],
        film["csfd_url"],
        move_to_top=True,
        move_to_list_id=inbox_list_id,
    )

    if card_id:
        yield f"Card already exists, updating: {trello.get_card_url(card_id)}"
        await trello.update_card(trello_api, card_id, card_data)
    else:
        yield "Card does not exist, creating"
        card_id = await trello.create_card(trello_api, card_data)
        yield f"Card created: {trello.get_card_url(card_id)}"

    yield "Updating members"
    await trello.join_card(trello_api, card_id, username)

    yield "Updating labels"
    labels = trello.prepare_duration_labels(film["durations"])
    if film.get("kvifftv_url"):
        labels.append(trello.KVIFFTV_LABEL)
    await trello.update_card_labels(trello_api, card_id, labels)

    yield "Updating attachments"
    await trello.update_card_attachments(
        trello_api,
        scraper,
        card_id,
        list(filter(None, [csfd_url, film["kvifftv_url"]])),
        film.get("poster_url"),
    )
    yield f"Done! This is your card: {trello.get_card_url(card_id)}"


async def get_csfd_url(scraper: httpx.AsyncClient, message_text: str) -> str:
    if input_url := csfd.get_kvifftv_url(message_text):
        logger.info(f"Detected KVIFF.TV URL, scraping: {input_url}")
        response = await scraper.get(input_url)
        if csfd_url := csfd.get_csfd_url(response.text):
            logger.info(f"Found CSFD.cz URL: {csfd_url}")
            return csfd_url
        raise ValueError("Could not find CSFD.cz URL")
    if input_url := csfd.get_csfd_url(message_text):
        logger.info(f"Detected CSFD.cz URL: {input_url}")
        return input_url
    raise ValueError("Could not find a valid film URL")


async def get_csfd_pages(
    scraper: httpx.AsyncClient,
    csfd_url: str,
) -> dict[str, http.Page]:
    pages = dict(csfd=await http.get_html(scraper, csfd_url))

    target_url = csfd.parse_target_url(pages["csfd"]["html"])
    try:
        pages["target"] = pages[target_url]
    except KeyError:
        logger.info(f"Different target URL, scraping: {target_url}")
        pages["target"] = await http.get_html(scraper, target_url)

    parent_url = csfd.get_parent_url(csfd_url)
    try:
        pages["parent"] = pages[parent_url]
    except KeyError:
        logger.info(f"Different parent URL, scraping: {parent_url}")
        pages["parent"] = await http.get_html(scraper, parent_url)

    return pages


def get_film(csfd_url: str, pages: dict[str, http.Page]) -> Film:
    return Film(
        csfd_url=csfd_url,
        title=csfd.parse_title(pages["target"]["html"]),
        poster_url=csfd.parse_poster_url(pages["target"]["html"]),
        durations=list(csfd.parse_durations(pages["target"]["html"])),
        kvifftv_url=csfd.parse_kvifftv_url(pages["parent"]["html"]),
    )


@trello.with_trello_api
@http.with_scraper
async def process_inbox(
    scraper: httpx.AsyncClient,
    trello_api: httpx.AsyncClient,
    board_id: str,
) -> None:
    inbox_list_id, archive_list_id = await trello.get_working_lists_ids(
        trello_api, board_id
    )

    years_ago = date.today() - timedelta(days=365 * 2)
    years_old_cards = await trello.get_old_cards(trello_api, inbox_list_id, years_ago)
    logger.info(f"Found {len(years_old_cards)} years old cards")
    for card in years_old_cards:
        logger.info(f"Archiving card: {card['name']} {trello.get_card_url(card['id'])}")
    await trello.archive_cards(trello_api, archive_list_id, years_old_cards)

    index = []

    cards = await trello.get_cards(trello_api, [inbox_list_id])
    for card in cards:
        logger.info(f"Processing: {card['name']} {trello.get_card_url(card['id'])}")
        if csfd_url := csfd.get_csfd_url(card["desc"]):
            logger.info(f"CSFD.cz URL: {csfd_url}")

            pages = await get_csfd_pages(scraper, csfd_url)
            film = get_film(csfd_url, pages)
            logger.info(f"Film:\n{pformat(film)}")

            logger.info(f"Updating: {card['name']} {trello.get_card_url(card['id'])}")
            card_data = trello.prepare_card_data(film["title"], film["csfd_url"])
            await trello.update_card(trello_api, card["id"], card_data)

            labels = trello.prepare_duration_labels(film["durations"])
            if film.get("kvifftv_url"):
                labels.append(trello.KVIFFTV_LABEL)
            await trello.update_card_labels(trello_api, card["id"], labels)

            await trello.update_card_attachments(
                trello_api,
                scraper,
                card["id"],
                list(filter(None, [csfd_url, film["kvifftv_url"]])),
                film.get("poster_url"),
            )

            index.append((card, film))
            logger.info(f"Done! {trello.get_card_url(card['id'])}")
        else:
            logger.info("Card description doesn't contain CSFD.cz URL")

    logger.info("Sorting cards")
    for position, (card, _) in enumerate(sorted(index, key=sort_inbox_key), start=1):
        logger.info(f"#{position}: {card['name']}")
        await trello.update_card_position(trello_api, card["id"], position)


def sort_inbox_key(index_item: tuple[dict, Film]) -> tuple[int, int, str]:
    card, film = index_item

    min_duration = min(film["durations"]) if (film and film["durations"]) else 1000
    labels = [label["name"].upper() for label in (card["labels"] or [])]
    is_available = (
        0
        if any(
            [
                availability_label in labels
                for availability_label in trello.AVAILABILITY_LABELS
            ]
        )
        else 1
    )

    return (min_duration, is_available, card["name"])
